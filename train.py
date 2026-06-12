# train.py

import cv2
import os
import numpy as np
from PIL import Image

def train_model():
    """Trains the LBPHFaceRecognizer on images found in the dataset directory."""
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    path = "dataset"
    
    if not os.path.exists(path):
        os.makedirs(path)
        
    faces = []
    ids = []
    
    # Filter for image files
    image_files = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        return False, "No training images found in 'dataset/' directory. Please capture faces first."
        
    for image in image_files:
        img_path = os.path.join(path, image)
        try:
            pil = Image.open(img_path).convert('L')
            imageNp = np.array(pil, 'uint8')
            
            # Expecting file format: User.[ID].[Count].jpg
            parts = image.split(".")
            if len(parts) >= 3 and parts[0] == 'User':
                student_id = int(parts[1])
                faces.append(imageNp)
                ids.append(student_id)
            else:
                print(f"Skipping file with unexpected name format: {image}")
        except Exception as e:
            print(f"Error loading image {image}: {e}")
            continue
            
    if not faces:
        return False, "No valid face samples parsed from the dataset."
        
    try:
        recognizer.train(faces, np.array(ids))
        trainer_dir = "trainer"
        if not os.path.exists(trainer_dir):
            os.makedirs(trainer_dir)
            
        recognizer.save(os.path.join(trainer_dir, 'trainer.yml'))
        num_students = len(set(ids))
        return True, f"Training complete! Trained on {len(faces)} images for {num_students} student(s)."
    except Exception as e:
        return False, f"Failed to train model: {str(e)}"

if __name__ == "__main__":
    success, message = train_model()
    print(message)