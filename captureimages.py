# captureimages.py

import cv2
import os

# Ensure dataset directory exists
dataset_dir = "dataset"
if not os.path.exists(dataset_dir):
    os.makedirs(dataset_dir)

cascade_path = 'haarcascade_frontalface_default.xml'
if not os.path.exists(cascade_path):
    print(f"Error: Cascade file '{cascade_path}' not found.")
    exit(1)

face_detector = cv2.CascadeClassifier(cascade_path)
if face_detector.empty():
    print(f"Error: Could not load cascade from '{cascade_path}'.")
    exit(1)

try:
    student_id = int(input("Enter Student ID: "))
except ValueError:
    print("Error: Student ID must be an integer.")
    exit(1)

cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("Error: Could not open webcam. Ensure no other application is using it.")
    exit(1)

print("Starting video capture. Position your face in front of the camera...")
print("Press ESC key to cancel.")

count = 0
while True:
    ret, img = cam.read()
    if not ret:
        print("Error: Failed to grab frame from camera.")
        break

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(30, 30)
    )

    for (x, y, w, h) in faces:
        count += 1
        # Save the cropped face image
        file_name = f"dataset/User.{student_id}.{count}.jpg"
        cv2.imwrite(file_name, gray[y:y+h, x:x+w])

        # Draw a rectangle around the face
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)

    cv2.imshow("Capturing Faces - Press ESC to Exit", img)

    # Wait for 100ms and check if ESC (ASCII 27) was pressed
    key = cv2.waitKey(100) & 0xFF
    if key == 27:
        print("Capture cancelled by user.")
        break
    elif count >= 100:
        print(f"Successfully captured {count} face samples!")
        break

cam.release()
cv2.destroyAllWindows()