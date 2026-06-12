# attendance.py

import cv2
import sqlite3
import os
from datetime import datetime
import database

class AttendanceTracker:
    def __init__(self, trainer_path='trainer/trainer.yml', cascade_path='haarcascade_frontalface_default.xml'):
        self.trainer_path = trainer_path
        self.cascade_path = cascade_path
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.is_loaded = False
        self.load_model()
        self.cam = None

    def load_model(self):
        """Loads or reloads the trained facial recognition model."""
        if os.path.exists(self.trainer_path):
            try:
                self.recognizer.read(self.trainer_path)
                self.is_loaded = True
                print("Face recognition model loaded successfully.")
                return True
            except Exception as e:
                print(f"Error loading face recognizer: {e}")
                self.is_loaded = False
                return False
        else:
            print("Trainer file not found. Face recognition is currently disabled.")
            self.is_loaded = False
            return False

    def start_camera(self):
        """Attempts to open the webcam camera if not already open."""
        if self.cam is None or not self.cam.isOpened():
            self.cam = cv2.VideoCapture(0)
        return self.cam.isOpened()

    def stop_camera(self):
        """Releases the camera device."""
        if self.cam is not None:
            self.cam.release()
            self.cam = None

    def detect_and_recognize(self, img):
        """Detects faces in the image and performs recognition using the trained model."""
        if self.face_cascade.empty():
            return img, []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        detected_students = []

        for (x, y, w, h) in faces:
            label_name = "Unknown"
            student_id = None
            confidence_pct = None
            
            if self.is_loaded:
                try:
                    student_id, confidence = self.recognizer.predict(gray[y:y+h, x:x+w])
                    
                    # confidence score (distance metric) - lower is better. 
                    # Generally under 60 is considered a good match.
                    if confidence < 60:
                        student = database.get_student_by_id(student_id)
                        if student:
                            label_name = student['name']
                            self._mark_attendance_if_needed(student_id, label_name)
                            detected_students.append({
                                'id': student_id,
                                'name': label_name,
                                'time': datetime.now().strftime("%H:%M:%S")
                            })
                        else:
                            label_name = f"ID {student_id} (Unregistered)"
                    confidence_pct = round(max(0, 100 - confidence))
                except Exception as e:
                    print(f"Face prediction failed: {e}")

            # Draw green bounding box for recognized students, red for unknown
            is_recognized = label_name != "Unknown" and "Unregistered" not in label_name
            box_color = (0, 255, 0) if is_recognized else (0, 0, 255)
            
            cv2.rectangle(img, (x, y), (x+w, y+h), box_color, 2)
            
            # Display text overlay
            text = f"{label_name}"
            if confidence_pct is not None:
                text += f" ({confidence_pct}%)"
            
            cv2.putText(
                img, 
                text, 
                (x + 5, y - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                (255, 255, 255), 
                2
            )

        return img, detected_students

    def _mark_attendance_if_needed(self, student_id, name):
        """Mark student attendance in the database if they haven't been marked present today."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date = ?", (student_id, date_str))
        already_marked = cursor.fetchone()
        conn.close()

        if not already_marked:
            database.mark_attendance(student_id, name, date_str, time_str)
            print(f"Attendance recorded: {name} (ID: {student_id}) at {time_str}")

    def generate_frames(self):
        """Yields JPEG frames for Flask streaming response."""
        if not self.start_camera():
            print("Error: Could not open camera for streaming.")
            return

        while True:
            ret, frame = self.cam.read()
            if not ret:
                break
            
            # Run AI pipeline
            frame, _ = self.detect_and_recognize(frame)
            
            # Compress and encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def run_cli():
    print("Starting CLI Attendance System...")
    tracker = AttendanceTracker()
    
    if not tracker.start_camera():
        print("Error: Cannot connect to webcam.")
        return
        
    print("Tracker started. Press 'ESC' on the camera window to close.")
    
    while True:
        ret, frame = tracker.cam.read()
        if not ret:
            print("Failed to capture image frame.")
            break
            
        frame, _ = tracker.detect_and_recognize(frame)
        cv2.imshow("Real-Time Attendance - CLI Mode", frame)
        
        # ESC key
        if cv2.waitKey(1) == 27:
            break
            
    tracker.stop_camera()
    cv2.destroyAllWindows()
    print("Tracker stopped.")

if __name__ == "__main__":
    database.init_db()
    run_cli()