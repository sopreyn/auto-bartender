import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import datetime

app = Flask(__name__)
CORS(app)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Load gender detection model
GENDER_PROTO = 'deploy_gender2.prototxt'
GENDER_MODEL = 'gender_net.caffemodel'
gender_net = cv2.dnn.readNetFromCaffe(GENDER_PROTO, GENDER_MODEL)
GENDER_LIST = ['Male', 'Female']

# Load age detection model
AGE_PROTO = 'deploy_age2.prototxt'
AGE_MODEL = 'age_net.caffemodel'
age_net = cv2.dnn.readNetFromCaffe(AGE_PROTO, AGE_MODEL)
AGE_BUCKETS = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']

print("Models loaded successfully.")

MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)

@app.route('/process-frame', methods=['POST'])
def process_frame():
    data = request.json.get('frame')

    # Decode base64 image from browser
    header, encoded = data.split(',', 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Add timestamp
    now = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    cv2.putText(frame, now, (10, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 2)

    # Face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    results = []

    for (x, y, w, h) in faces:
        center = (x + w // 2, y + h // 2)
        radius = int(max(w, h) / 2 * 1.2)
        cv2.circle(frame, center, radius, (0, 0, 255), 3)

        # Crop face  
'''
import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import datetime

app = Flask(__name__)
CORS(app)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

@app.route('/process-frame', methods=['POST'])
def process_frame():
    data = request.json.get('frame')
    
    # Decode base64 image from browser
    header, encoded = data.split(',', 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Add timestamp
    now = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    cv2.putText(frame, now, (10, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 2)

    # Face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Re-encode and send back
    _, buffer = cv2.imencode('.jpg', frame)
    result_b64 = base64.b64encode(buffer).decode('utf-8')

    return jsonify({
        'frame': f'data:image/jpeg;base64,{result_b64}',
        'faces_detected': len(faces),
        'timestamp': now
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
'''
