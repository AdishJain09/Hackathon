# from flask import Flask, render_template, Response
# import cv2
# import mediapipe as mp
# import threading
# import time
# import pyaudio
# import numpy as np
# import pygetwindow as gw
# import platform
# import subprocess

# app = Flask(__name__)

# # Mediapipe setup
# mp_face_detection = mp.solutions.face_detection
# mp_drawing = mp.solutions.drawing_utils

# # Constants
# TAB_CHECK_INTERVAL = 2
# HEAD_SHIFT_THRESHOLD = 20
# NO_FACE_THRESHOLD = 30
# NO_OF_FACES_THRESHOLD = 1
# VOICE_THRESHOLD = 5000

# # Global variables
# alerts = []
# prev_face_coords = None
# no_face_counter = 0

# def monitor_tab_switching():
#     previous_window = gw.getActiveWindow().title if gw.getActiveWindow() else None
#     while True:
#         current_window = gw.getActiveWindow()
#         if current_window and current_window.title != previous_window:
#             alerts.append("Tab switching detected!")
#             print("Alert added: Tab switching detected!")  # Debugging
#             previous_window = current_window.title
#         time.sleep(TAB_CHECK_INTERVAL)


# def detect_face_shifts_and_multiple_faces(frame, face_detection):
#     global prev_face_coords, no_face_counter

#     results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#     if results.detections:
#         no_face_counter = 0
#         face_count = len(results.detections)

#         if face_count > NO_OF_FACES_THRESHOLD:
#             alerts.append(f"Multiple faces detected: {face_count}!")

#         detection = results.detections[0]
#         bboxC = detection.location_data.relative_bounding_box
#         h, w, _ = frame.shape
#         current_coords = (
#             int(bboxC.xmin * w),
#             int(bboxC.ymin * h),
#             int(bboxC.width * w),
#             int(bboxC.height * h),
#         )

#         if prev_face_coords:
#             shift_distance = ((prev_face_coords[0] - current_coords[0]) ** 2 + (prev_face_coords[1] - current_coords[1]) ** 2) ** 0.5
#             if shift_distance > HEAD_SHIFT_THRESHOLD:
#                 alerts.append("Face shift detected!")

#         prev_face_coords = current_coords

#     else:
#         no_face_counter += 1
#         if no_face_counter >= NO_FACE_THRESHOLD:
#             alerts.append("No face detected!")

# def monitor_sound_levels():
#     p = pyaudio.PyAudio()
#     stream = p.open(
#         format=pyaudio.paInt16,
#         channels=1,
#         rate=44100,
#         input=True,
#         frames_per_buffer=1024,
#     )

#     while True:
#         data = stream.read(1024, exception_on_overflow=False)
#         audio_data = np.frombuffer(data, dtype=np.int16)
#         volume = np.linalg.norm(audio_data)

#         if volume > VOICE_THRESHOLD:
#             alerts.append("Loud noise detected!")
#             time.sleep(1)  # Cooldown period

# def detect_vm_environment():
#     vm_indicators = ["VirtualBox", "VMware", "Hyper-V", "QEMU", "Parallels"]
#     try:
#         if platform.system() == "Windows":
#             bios_info = subprocess.check_output("wmic bios get smbiosbiosversion", shell=True).decode()
#         else:
#             bios_info = subprocess.check_output("dmidecode -s bios-version", shell=True).decode()

#         for indicator in vm_indicators:
#             if indicator.lower() in bios_info.lower():
#                 alerts.append(f"Virtual Machine detected ({indicator})!")
#                 break
#     except Exception as e:
#         alerts.append(f"Error detecting VM environment: {e}")

# @app.route('/')
# def index():
#     return render_template('index.html', alerts=alerts)


# def generate_video_feed():
#     cap = cv2.VideoCapture(0)
#     with mp_face_detection.FaceDetection(min_detection_confidence=0.7) as face_detection:
#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             detect_face_shifts_and_multiple_faces(frame, face_detection)

#             _, buffer = cv2.imencode('.jpg', frame)
#             frame = buffer.tobytes()

#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

#     cap.release()

# @app.route('/video_feed')
# def video_feed():
#     return Response(generate_video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

# if __name__ == "__main__":
#     threading.Thread(target=monitor_tab_switching, daemon=True).start()
#     threading.Thread(target=monitor_sound_levels, daemon=True).start()
#     detect_vm_environment()
#     app.run(debug=True, host='0.0.0.0')

from flask import Flask, render_template, Response
from flask import jsonify
import cv2
import mediapipe as mp
import threading
import time
import pyaudio
import numpy as np
import pygetwindow as gw
import platform
import subprocess
from threading import Lock

app = Flask(__name__)

@app.route('/get_alerts')
def get_alerts():
    return jsonify(alerts)


# Mediapipe setup
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

# Constants
TAB_CHECK_INTERVAL = 2
HEAD_SHIFT_THRESHOLD = 20
NO_FACE_THRESHOLD = 30
NO_OF_FACES_THRESHOLD = 1
VOICE_THRESHOLD = 5000
ALERTS_MAX_SIZE = 10  # Limit the size of the alerts list to avoid clutter

# Global variables
alerts = []
alerts_lock = Lock()  # Lock for thread-safe access to alerts
prev_face_coords = None
no_face_counter = 0


def add_alert(message):
    """Safely add an alert to the global alerts list."""
    with alerts_lock:
        if len(alerts) >= ALERTS_MAX_SIZE:
            alerts.pop(0)  # Remove the oldest alert if the list is full
        alerts.append(message)
        print(f"Alert added: {message}")  # Debugging


def monitor_tab_switching():
    """Monitor tab switching."""
    previous_window = gw.getActiveWindow().title if gw.getActiveWindow() else None
    while True:
        current_window = gw.getActiveWindow()
        if current_window and current_window.title != previous_window:
            add_alert("Tab switching detected!")
            previous_window = current_window.title
        time.sleep(TAB_CHECK_INTERVAL)


def detect_face_shifts_and_multiple_faces(frame, face_detection):
    """Detect face shifts and multiple faces."""
    global prev_face_coords, no_face_counter

    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if results.detections:
        no_face_counter = 0
        face_count = len(results.detections)

        if face_count > NO_OF_FACES_THRESHOLD:
            add_alert(f"Multiple faces detected: {face_count}!")

        detection = results.detections[0]
        bboxC = detection.location_data.relative_bounding_box
        h, w, _ = frame.shape
        current_coords = (
            int(bboxC.xmin * w),
            int(bboxC.ymin * h),
            int(bboxC.width * w),
            int(bboxC.height * h),
        )

        if prev_face_coords:
            shift_distance = ((prev_face_coords[0] - current_coords[0]) ** 2 + (prev_face_coords[1] - current_coords[1]) ** 2) ** 0.5
            if shift_distance > HEAD_SHIFT_THRESHOLD:
                add_alert("Face shift detected!")

        prev_face_coords = current_coords
    else:
        no_face_counter += 1
        if no_face_counter >= NO_FACE_THRESHOLD:
            add_alert("No face detected!")


def monitor_sound_levels():
    """Monitor sound levels for loud noises."""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=44100,
        input=True,
        frames_per_buffer=1024,
    )

    while True:
        data = stream.read(1024, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        volume = np.linalg.norm(audio_data)

        if volume > VOICE_THRESHOLD:
            add_alert("Loud noise detected!")
            time.sleep(1)  # Cooldown period


def detect_vm_environment():
    """Detect if the script is running inside a virtual machine."""
    vm_indicators = ["VirtualBox", "VMware", "Hyper-V", "QEMU", "Parallels"]
    try:
        if platform.system() == "Windows":
            bios_info = subprocess.check_output("wmic bios get smbiosbiosversion", shell=True).decode()
        else:
            bios_info = subprocess.check_output("dmidecode -s bios-version", shell=True).decode()

        for indicator in vm_indicators:
            if indicator.lower() in bios_info.lower():
                add_alert(f"Virtual Machine detected ({indicator})!")
                break
    except Exception as e:
        add_alert(f"Error detecting VM environment: {e}")


@app.route('/')
def index():
    """Render the main page."""
    with alerts_lock:
        return render_template('index.html', alerts=alerts)


def generate_video_feed():
    """Generate a live video feed."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        add_alert("Unable to access camera!")
        return

    with mp_face_detection.FaceDetection(min_detection_confidence=0.7) as face_detection:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            detect_face_shifts_and_multiple_faces(frame, face_detection)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()


@app.route('/video_feed')
def video_feed():
    """Route for the video feed."""
    return Response(generate_video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    threading.Thread(target=monitor_tab_switching, daemon=True).start()
    print("Tab switching monitor started")

    threading.Thread(target=monitor_sound_levels, daemon=True).start()
    print("Sound monitor started")

    detect_vm_environment()
    print("VM detection completed")

    app.run(debug=True, host='0.0.0.0')
