import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import csv
import datetime
import os

import joblib
import pandas as pd

from features import AGE_BUCKETS, DRINKS, GENDER_LIST, ORDER_COLUMNS, encode

app = Flask(__name__)
CORS(app)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

# Load gender detection model
GENDER_PROTO = 'deploy_gender2.prototxt'
GENDER_MODEL = 'gender_net.caffemodel'
gender_net = cv2.dnn.readNetFromCaffe(GENDER_PROTO, GENDER_MODEL)

# Load age detection model
AGE_PROTO = 'deploy_age2.prototxt'
AGE_MODEL = 'age_net.caffemodel'
age_net = cv2.dnn.readNetFromCaffe(AGE_PROTO, AGE_MODEL)

print("Models loaded successfully.")

MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)

ORDERS_CSV = 'orders.csv'
MODEL_PATH = 'drink_model.joblib'

# Trained by train.py; until then fall back to the hand-written rules
drink_model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
print("Loaded trained drink model." if drink_model else "No trained drink model, using rules.")


def rule_based_rec(gender, age, is_smiling):
    if gender == "Male" and age in ['(15-20)', '(25-32)'] and is_smiling:
        return "Light Beer"
    elif gender == "Female" and age in ['(25-32)', '(38-43)'] and is_smiling:
        return "Soju"
    else:
        return "Wine"


def drink_rec(gender, age, is_smiling, dt):
    """Return the top 3 drinks as [{'drink', 'probability'}], best first."""
    if drink_model is None:
        return [{'drink': rule_based_rec(gender, age, is_smiling), 'probability': None}]

    model, columns = drink_model['model'], drink_model['columns']
    features = encode(gender, age, is_smiling, dt)
    probs = model.predict_proba([[features[c] for c in columns]])[0]
    top = probs.argsort()[::-1][:3]
    return [{'drink': str(model.classes_[i]), 'probability': float(probs[i])} for i in top]


@app.route('/drinks', methods=['GET'])
def drinks():
    return jsonify({'drinks': DRINKS})


@app.route('/log-order', methods=['POST'])
def log_order():
    """Save one patron's detected features plus what they actually ordered."""
    order = request.json or {}
    if order.get('drink') not in DRINKS:
        return jsonify({'error': f"drink must be one of {DRINKS}"}), 400
    if order.get('gender') not in GENDER_LIST or order.get('age') not in AGE_BUCKETS:
        return jsonify({'error': 'missing or unknown gender/age'}), 400

    row = {
        'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
        'gender': order['gender'],
        'gender_confidence': float(order.get('gender_confidence', 0)),
        'age': order['age'],
        'age_confidence': float(order.get('age_confidence', 0)),
        'is_smiling': int(bool(order.get('is_smiling'))),
        'faces_detected': int(order.get('faces_detected', 1)),
        'drink': order['drink'],
    }
    is_new = not os.path.exists(ORDERS_CSV)
    with open(ORDERS_CSV, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=ORDER_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    return jsonify({'logged': row})


@app.route('/process-frame', methods=['POST'])
def process_frame():
    data = request.json.get('frame')

    # Decode base64 image from browser
    header, encoded = data.split(',', 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    now_dt = datetime.datetime.now()
    now = now_dt.strftime("%m/%d/%Y %H:%M:%S")
    
    # Face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    results = []
    frame_h, frame_w = frame.shape[:2]

    for (x, y, w, h) in faces:
        center = (x + w // 2, y + h // 2)
        radius = int(max(w, h) / 2 * 1.2)
        cv2.circle(frame, center, radius, (0, 0, 255), 3)

        # Separate grayscale region just for this specific face to search for a smile
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]
        
        # Smile detection parameters optimized for face sub-regions:
        # minNeighbors=20+ avoids false-positive twitch detections
        smiles = smile_cascade.detectMultiScale(roi_gray, scaleFactor=1.7, minNeighbors=22)
        
        is_smiling = False
        for (sx, sy, sw, sh) in smiles:
            # Draw a green rectangle around the mouth inside the face region
            cv2.rectangle(roi_color, (sx, sy), (sx + sw, sy + sh), (0, 255, 255), 2)
            is_smiling = True

        # Crop face with a little padding for DNN processing, clamped to frame bounds
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

        # Update text label overlay to include expression status
        mood_text = "Smiling" if is_smiling else "Neutral"
        label = f"{gender}, {age} ({mood_text})"
        label_y = max(0, y1 - 10)
        cv2.putText(
            frame, label, (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )


        recs = drink_rec(gender, age, is_smiling, now_dt)
        results.append({
            'box': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
            'gender': gender,
            'gender_confidence': gender_confidence,
            'age': age,
            'age_confidence': age_confidence,
            'is_smiling': is_smiling,
            'drink_rec': recs[0]['drink'],
            'drink_recs': recs,
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