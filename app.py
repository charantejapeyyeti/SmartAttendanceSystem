# app.py

import os
import re
import base64
import numpy as np
import cv2
from flask import Flask, render_template, jsonify, request, Response
from datetime import datetime

import database
from attendance import AttendanceTracker
from train import train_model
from risk_predictor import RiskPredictor

# Initialize Flask App
app = Flask(__name__, template_folder='templates', static_folder='static')

# Ensure directories exist
os.makedirs('dataset', exist_ok=True)
os.makedirs('trainer', exist_ok=True)

# Initialize database schema
database.init_db()

# Initialize AI Modules
tracker = AttendanceTracker()
risk_predictor = RiskPredictor()

# Load cascade for server-side validation during browser photo uploads
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

@app.route('/')
def home():
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Calculates summary statistics for the dashboard."""
    students = database.get_all_students()
    total_students = len(students)
    
    # Calculate total class days (unique attendance dates)
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT date) as count FROM attendance")
    total_days = cursor.fetchone()['count'] or 0
    
    # Calculate attendance logs count
    cursor.execute("SELECT COUNT(*) as count FROM attendance")
    total_logs = cursor.fetchone()['count'] or 0
    conn.close()
    
    # Calculate individual attendance rates and risk counts
    at_risk_count = 0
    total_pct_sum = 0
    
    for s in students:
        s_id = s['id']
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT date) as count FROM attendance WHERE student_id = ?", (s_id,))
        attended_days = cursor.fetchone()['count'] or 0
        conn.close()
        
        att_pct = (attended_days / total_days * 100) if total_days > 0 else 100.0
        total_pct_sum += att_pct
        
        # Predict risk using scikit-learn (using attendance rate, and assuming average score of 70 for internal/assignments)
        prediction = risk_predictor.predict(att_pct, 70, 70)
        if prediction == "Fail" or att_pct < 75.0:
            at_risk_count += 1
            
    avg_attendance = (total_pct_sum / total_students) if total_students > 0 else 100.0
    
    return jsonify({
        'total_students': total_students,
        'total_days': total_days,
        'total_logs': total_logs,
        'avg_attendance': round(avg_attendance, 1),
        'at_risk_students': at_risk_count
    })

@app.route('/api/students', methods=['GET', 'POST'])
def handle_students():
    """Gets all students or registers a new student."""
    if request.method == 'GET':
        students = database.get_all_students()
        
        # Enrich with attendance rates
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT date) as count FROM attendance")
        total_days = cursor.fetchone()['count'] or 0
        conn.close()
        
        enriched_students = []
        for s in students:
            s_id = s['id']
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT date) as count FROM attendance WHERE student_id = ?", (s_id,))
            attended = cursor.fetchone()['count'] or 0
            conn.close()
            
            att_pct = (attended / total_days * 100) if total_days > 0 else 100.0
            
            # Predict risk using default grades (70% internal, 70% assignments)
            risk = risk_predictor.predict(att_pct, 70, 70)
            
            enriched_students.append({
                'id': s['id'],
                'name': s['name'],
                'attended_classes': attended,
                'attendance_percentage': round(att_pct, 1),
                'risk_status': risk
            })
            
        return jsonify(enriched_students)
        
    elif request.method == 'POST':
        data = request.json
        student_id = data.get('id')
        name = data.get('name', '').strip()
        
        if not student_id or not name:
            return jsonify({'success': False, 'message': 'Student ID and Name are required'}), 400
            
        try:
            student_id = int(student_id)
        except ValueError:
            return jsonify({'success': False, 'message': 'Student ID must be a numeric integer'}), 400
            
        # Add to database
        if database.add_student(student_id, name):
            return jsonify({'success': True, 'message': f'Student {name} registered in database successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to insert student into database'}), 500

@app.route('/api/upload_face', methods=['POST'])
def upload_face():
    """Receives camera snapshots from the browser and saves them as dataset images."""
    data = request.json
    student_id = data.get('student_id')
    count = data.get('count')
    image_b64 = data.get('image')
    
    if not student_id or not count or not image_b64:
        return jsonify({'success': False, 'message': 'Missing parameter'}), 400
        
    try:
        # Decode base64 image data
        image_data = re.sub('^data:image/.+;base64,', '', image_b64)
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect face
        faces = face_detector.detectMultiScale(
            gray, 
            scaleFactor=1.2, 
            minNeighbors=5, 
            minSize=(50, 50)
        )
        
        if len(faces) > 0:
            # Crop the first detected face
            (x, y, w, h) = faces[0]
            cropped = gray[y:y+h, x:x+w]
            
            # Save image
            filename = f"dataset/User.{student_id}.{count}.jpg"
            cv2.imwrite(filename, cropped)
            return jsonify({'success': True, 'message': f'Face sample {count}/100 saved.'})
        else:
            return jsonify({'success': False, 'message': 'No face detected in photo. Reposition your head.'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to process image: {str(e)}'}), 500

@app.route('/api/train', methods=['POST'])
def trigger_training():
    """Triggers the training of the LBPH face recognition model."""
    success, message = train_model()
    if success:
        # Reload the tracker recognizer model
        tracker.load_model()
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/api/video_feed')
def video_feed():
    """MJPEG streaming endpoint for live webcam feed with AI overlay."""
    # Ensure tracker reloads model in case it was just trained
    tracker.load_model()
    return Response(
        tracker.generate_frames(), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/stop_camera', methods=['POST'])
def stop_camera():
    """Closes the webcam connection on the server."""
    tracker.stop_camera()
    return jsonify({'success': True, 'message': 'Webcam deactivated successfully.'})

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    """Retrieves recent attendance logs."""
    logs = database.get_attendance_logs(100)
    return jsonify(logs)

@app.route('/api/predict_risk', methods=['POST'])
def predict_risk():
    """Runs scikit-learn Decision Tree model to predict student risk."""
    data = request.json
    try:
        att = float(data.get('attendance', 0))
        internal = float(data.get('internal', 0))
        assign = float(data.get('assignment', 0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid numeric score inputs'}), 400
        
    result = risk_predictor.predict(att, internal, assign)
    
    # Calculate risk description
    is_at_risk = result == "Fail" or att < 75.0
    risk_level = "High" if is_at_risk else "Low"
    color = "danger" if is_at_risk else "success"
    
    message = (
        f"This student is classified as AT RISK ({risk_level} Risk). Their expected result is Fail. "
        f"Please recommend academic intervention." if is_at_risk else
        f"This student has a LOW RISK level. Their expected result is Pass."
    )
    
    return jsonify({
        'success': True,
        'result': result,
        'risk_level': risk_level,
        'color': color,
        'message': message
    })

if __name__ == '__main__':
    # Start flask app
    app.run(debug=True, host='127.0.0.1', port=5000)