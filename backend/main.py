import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import datetime
import pandas as pd

app = Flask(__name__)
CORS(app)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

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

drink_data = {
    "drink_name": ["Light Beer", "Soju", "Wine", "Hard Cider", "Old Fashioned"],
    "recommended_age_group": [2, 3, 4, 2, 4],
    "preferred_gender": ["Male", "Any", "Female", "Female", "Male"],
    "abv": [4.2, 20.0, 12.0, 6.0, 32.0]
}

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
    #cv2.putText(frame, now, (10, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 2)
    
    # Face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    results = []
    frame_h, frame_w = frame.shape[:2]

    for (x, y, w, h) in faces:
        center = (x + w // 2, y + h // 2)
        radius = int(max(w, h) / 2 * 1.2)
        cv2.circle(frame, center, radius, (0, 0, 255), 3)

        # Crop face with a little padding, clamped to frame bounds
        pad = int(0.05 * h)
        y1 = max(0, y - pad)
        y2 = min(frame_h, y + h + pad)
        x1 = max(0, x - pad)
        x2 = min(frame_w, x + w + pad)
        face_img = frame[y1:y2, x1:x2]

        if face_img.size == 0:
            continue

        # Build blob for the DNN models
        blob = cv2.dnn.blobFromImage(
            face_img, 1.0, (227, 227),
            MODEL_MEAN_VALUES, swapRB=True
        )

        # Gender prediction
        gender_net.setInput(blob)
        gender_preds = gender_net.forward()
        gender = GENDER_LIST[gender_preds[0].argmax()]
        gender_confidence = float(gender_preds[0].max())

        # Age prediction
        age_net.setInput(blob)
        age_preds = age_net.forward()
        age = AGE_BUCKETS[age_preds[0].argmax()]
        age_confidence = float(age_preds[0].max())

        # Draw label above the detected face
        label = f"{gender}, {age}"
        label_y = max(0, y1 - 10)
        cv2.putText(
            frame, label, (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )

        results.append({
            'box': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
            'gender': gender,
            'gender_confidence': gender_confidence,
            'age': age,
            'age_confidence': age_confidence
        })

    # Re-encode and send back
    _, buffer = cv2.imencode('.jpg', frame)
    result_b64 = base64.b64encode(buffer).decode('utf-8')

    return jsonify({
        'frame': f'data:image/jpeg;base64,{result_b64}',
        'faces_detected': len(faces),
        'results': results,
        'timestamp': now
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)
