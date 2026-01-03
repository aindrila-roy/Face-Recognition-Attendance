
import streamlit as st
import pandas as pd
import time
from datetime import datetime
import os
from streamlit_autorefresh import st_autorefresh

# Set page title
st.set_page_config(page_title="Attendance System", layout="wide")
st.title("Attendance Monitoring System")

# Get current date for the filename
ts = time.time()
date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")

# Automatic refresh every 2 seconds to show new attendance
st_autorefresh(interval=2000, limit=100, key="datarefresh")

# Define the path to your CSV file
attendance_path = f"./Attendance/Attendance_{date}.csv"

# Display date on UI
st.subheader(f"📅 Attendance for {date}")

# Check if the file exists before trying to read it
if os.path.isfile(attendance_path):
    try:
        df = pd.read_csv(attendance_path)
        
        # Define the expected columns
        expected_columns = ['Roll Number', 'Name', 'Department', 'Semester', 'Time', 'Snapshot Path']
        
        if len(df.columns) == len(expected_columns):
            df.columns = expected_columns
        elif len(df.columns) == 5: 
            # Handle the case where an older 5-column file might exist
            df.columns = ['Roll Number', 'Name', 'Department', 'Semester', 'Time']
            
        df.index = df.index + 1
        df.index.name = "S.No"
        # Display the attendance table
        st.dataframe(df, use_container_width=True)
        
        st.write(f"Total entries: {len(df)}")
        
    except Exception as e:
        st.error(f"Error reading file: {e}")
else:
    st.info("No attendance recorded yet for today.")
    st.write("Run the face recognition script (`test.py`) to log attendance.")