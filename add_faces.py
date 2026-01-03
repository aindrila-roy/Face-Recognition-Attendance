import cv2
import pickle
import numpy as np
import os

# Initialize video and detector
video = cv2.VideoCapture(0)

# Ensure path uses ./ for stability
facedetect = cv2.CascadeClassifier('./data/haarcascade_frontalface_default.xml')

faces_data = []
i = 0

# Ensure data and Attendance directories exist
if not os.path.exists('data'):
    os.makedirs('data')
if not os.path.exists('Attendance'):
    os.makedirs('Attendance')
    
# Create Snapshots base directory
if not os.path.exists('./Attendance/Snapshots'):
    os.makedirs('./Attendance/Snapshots')

# --- USER INPUT FIELDS ---
name = input("Enter Your Name: ")
department = input("Enter Your Department: ")
semester = input("Enter Your Semester: ")
roll_number = input("Enter Your Roll Number: ")

# Create the unique label for KNN training (must be parsable by test.py)
unique_label = f"{roll_number}_{name}_{department}_{semester}"
# -------------------------

print("\n--- Starting Face Data Collection (100 samples required) ---\n")

while True:
    ret, frame = video.read()
    if not ret:
        break
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)
    
    for (x, y, w, h) in faces:
        crop_img = frame[y:y+h, x:x+w, :]
        resized_img = cv2.resize(crop_img, (50, 50))
        
        # Capture 100 samples, 1 every 10 frames
        if len(faces_data) < 100 and i % 10 == 0:
            faces_data.append(resized_img)
        
        i += 1
        cv2.putText(frame, str(len(faces_data)), (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 255), 1)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 1)
        
    cv2.imshow("Registration Frame", frame)
    k = cv2.waitKey(1)
    
    # Stop when 100 samples are collected or 'q' is pressed
    if k == ord('q') or len(faces_data) == 100:
        break

video.release()
cv2.destroyAllWindows()

# Process data into numpy array
faces_data = np.asarray(faces_data)
faces_data = faces_data.reshape(100, -1)

# Handle labels (names.pkl)
names_path = 'data/names.pkl'
if not os.path.exists(names_path):
    names = [unique_label] * 100
    with open(names_path, 'wb') as f:
        pickle.dump(names, f)
else:
    with open(names_path, 'rb') as f:
        names = pickle.load(f)
    names = names + [unique_label] * 100
    with open(names_path, 'wb') as f:
        pickle.dump(names, f)

# Handle face embeddings (faces_data.pkl)
faces_path = 'data/faces_data.pkl'
if not os.path.exists(faces_path):
    with open(faces_path, 'wb') as f:
        pickle.dump(faces_data, f)
else:
    with open(faces_path, 'rb') as f:
        faces = pickle.load(f)
    faces = np.append(faces, faces_data, axis=0)
    with open(faces_path, 'wb') as f:
        pickle.dump(faces, f)

print(f"\nRegistration for {name} ({roll_number}) complete! Data points: {len(faces_data)}\n")