from sklearn.neighbors import KNeighborsClassifier
import cv2
import pickle
import numpy as np
import os
import csv
import time
from datetime import datetime
from win32com.client import Dispatch

# Global dictionary to track the last time an "ALREADY TAKEN" message was spoken
# This prevents constant voice repetition for already logged users.
LAST_ALREADY_TAKEN_SPEAK_TIME = {}
SPEAK_DELAY_SECONDS = 5 # Minimum delay required for speaking duplicate attendance

def speak(str1):
    speak_engine = Dispatch("SAPI.SpVoice")
    speak_engine.Speak(str1)

# --- UI CONSTANTS (For background.png and smaller window) ---
# NOTE: These coordinates are for a smaller window/image (approx 1000x800).
CAMERA_X_OFFSET = 55  
CAMERA_Y_OFFSET = 162
CAMERA_WIDTH = 640  
CAMERA_HEIGHT = 480 

# Coordinates for text elements (These may need minor adjustment)
STATUS_BOX_POS = (60, 670)  # Left status box
LAST_LOG_POS = (280, 670)   # Middle status box
COUNT_BOX_POS = (500, 670)  # Right status box

TEXT_COLOR = (255, 255, 255) 
FONT_SCALE = 0.5 
# -------------------------------------------------------------------------

# Initialize camera and detector
video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier('./data/haarcascade_frontalface_default.xml')

# Check if data files exist before loading
names_path = './data/names.pkl'
faces_path = './data/faces_data.pkl'
if not os.path.exists(names_path) or not os.path.exists(faces_path):
    print("Error: Data files not found. Please run add_faces.py first.")
    exit()

with open(names_path, 'rb') as w:
    LABELS = pickle.load(w)
with open(faces_path, 'rb') as f:
    FACES = pickle.load(f)

# Train the model
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(FACES, LABELS)

# --- LOAD THE SPECIFIC BACKGROUND IMAGE ---
imgBackground = cv2.imread("background.png") 
if imgBackground is None:
    print("Error: background.png not found or failed to load. Using plain camera feed.")

# --- ATTENDANCE TRACKING SETUP (Daily Check) ---
COL_NAMES = ['ROLL_NUMBER', 'NAME', 'DEPARTMENT', 'SEMESTER', 'TIME', 'SNAPSHOT_PATH']
ts = time.time()
date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
attendance_path = "./Attendance/Attendance_" + date + ".csv"
exist = os.path.isfile(attendance_path)

daily_present = set()
if exist:
    try:
        with open(attendance_path, 'r', newline='') as f:
            reader = csv.reader(f)
            if os.path.getsize(attendance_path) > 0: 
                 header = next(reader)
                 for row in reader:
                    if len(row) > 0:
                        daily_present.add(row[0]) 
    except Exception as e:
        print(f"Error loading daily attendance from CSV: {e}")

snapshot_dir = f"./Attendance/Snapshots/{date}"
if not os.path.exists(snapshot_dir):
    os.makedirs(snapshot_dir)
# -----------------------------------------------

print(f"\n--- Starting Attendance Session (Automatic Logging, Press 'Q' to quit) ---\n")
last_logged_name = "N/A" 

while True:
    ret, frame = video.read()
    if not ret:
        break
    
    # --- Prepare Display Frame ---
    if imgBackground is not None:
        display_frame = imgBackground.copy()
        resized_camera = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT)) 
        display_frame[CAMERA_Y_OFFSET:CAMERA_Y_OFFSET + CAMERA_HEIGHT, 
                      CAMERA_X_OFFSET:CAMERA_X_OFFSET + CAMERA_WIDTH] = resized_camera
    else:
        display_frame = frame
    
    # Initial status texts
    current_attendance_count = len(daily_present) 
    status_text = "STATUS: DETECTING..."
    last_log_text = f"LAST LOG: {last_logged_name}"
    count_text = f"TODAY'S COUNT: {current_attendance_count}"

    # Draw initial UI text
    cv2.putText(display_frame, count_text, COUNT_BOX_POS, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 2)
    cv2.putText(display_frame, last_log_text, LAST_LOG_POS, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 2)
    cv2.putText(display_frame, status_text, STATUS_BOX_POS, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 2)

    # --- Face Detection and Logic ---
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        crop_img = frame[y:y+h, x:x+w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        
        try:
            output = knn.predict(resized_img)[0]
        except ValueError:
            output = 'Error'

        # Draw box and label on the live camera feed area
        if imgBackground is not None:
            # Drawing the box requires explicit integer tuples with UI offset
            pt1 = (int(CAMERA_X_OFFSET + x), int(CAMERA_Y_OFFSET + y))
            pt2 = (int(CAMERA_X_OFFSET + x + w), int(CAMERA_Y_OFFSET + y + h))
            text_pos = (int(CAMERA_X_OFFSET + x), int(CAMERA_Y_OFFSET + y - 15))

            cv2.rectangle(display_frame, pt1, pt2, (0, 255, 0), 2)
            cv2.putText(display_frame, output, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # --- AUTOMATIC ATTENDANCE LOGIC ---
        if output not in ['Unknown', 'Error']:
            try:
                parts = output.split('_')
                if len(parts) >= 4:
                    roll_number, name_full, department, semester = parts[0], parts[1], parts[2], parts[3]
                else:
                    roll_number, name_full, department, semester = parts[0], parts[1], "N/A", "N/A"
                
                timestamp_log = datetime.fromtimestamp(time.time()).strftime("%H:%M:%S")

                if roll_number in daily_present:
                    # 1. ALREADY PRESENT (Speak with 5-second delay check)
                    status_text = "STATUS: PRESENT LOGGED"
                    current_time = time.time()
                    last_speak_time = LAST_ALREADY_TAKEN_SPEAK_TIME.get(roll_number, 0)
                    
                    if (current_time - last_speak_time) > SPEAK_DELAY_SECONDS:
                        speak("Attendance already recorded for today.")
                        LAST_ALREADY_TAKEN_SPEAK_TIME[roll_number] = current_time
                    
                else:
                    # 2. LOG ATTENDANCE (First time today)
                    status_text = "STATUS: LOGGING NEW ENTRY"
                    
                    snapshot_filename = f"{roll_number}_{date}_{int(time.time())}.jpg"
                    snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
                    cv2.imwrite(snapshot_path, crop_img) 
                    
                    attendance = [roll_number, name_full, department, semester, timestamp_log, snapshot_path]
                    
                    with open(attendance_path, "a", newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        if not exist or os.path.getsize(attendance_path) == 0: 
                            writer.writerow(COL_NAMES)
                        writer.writerow(attendance)
                    
                    daily_present.add(roll_number)
                    last_logged_name = name_full # Update the last logged name
                    speak(f"Attendance recorded for {name_full}.") 
                    
            except Exception as e:
                status_text = "ID PROCESSING ERROR"
                print(f"Skipping logging due to error: {e}")

        # --- Update the dynamic UI text with the latest status ---
        cv2.putText(display_frame, status_text, STATUS_BOX_POS, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 2)
        cv2.putText(display_frame, last_log_text, LAST_LOG_POS, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 2)
        cv2.putText(display_frame, count_text, COUNT_BOX_POS, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 2)
        # --- END ATTENDANCE LOGIC ---

    # Show the final UI image
    cv2.imshow("FACIAL RECOGNITION & ATTENDANCE SYSTEM", display_frame)

    k = cv2.waitKey(1)
    
    # --- QUIT TRIGGER: PRESS 'Q' ---
    if k == ord('q'):
        break

video.release()
cv2.destroyAllWindows()