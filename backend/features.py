"""Shared feature encoding for logging orders, training, and live prediction.

orders.csv stores the raw detections (e.g. "Male", "(25-32)") so the encoding
here can change later without re-collecting data.
"""
import datetime

DRINKS = ["Light Beer", "Soju", "Wine", "Hard Cider", "Old Fashioned"]

GENDER_LIST = ['Male', 'Female']
AGE_BUCKETS = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']

ORDER_COLUMNS = [
    'timestamp', 'gender', 'gender_confidence', 'age', 'age_confidence',
    'is_smiling', 'faces_detected', 'drink',
]

# Each feature is a small non-negative integer category, as CategoricalNB expects.
# The value is the number of categories, so unseen values still get a probability.
FEATURES = {
    'gender': len(GENDER_LIST),
    'age': len(AGE_BUCKETS),
    'is_smiling': 2,
    'time_of_day': 4,
    'is_weekend': 2,
}
FACE_FEATURES = ['gender', 'age', 'is_smiling']
TIME_FEATURES = ['time_of_day', 'is_weekend']


def time_of_day(dt):
    # 0 = before 5pm, 1 = 5-8pm, 2 = 8-11pm, 3 = late night (11pm-5am)
    if 5 <= dt.hour < 17:
        return 0
    if 17 <= dt.hour < 20:
        return 1
    if 20 <= dt.hour < 23:
        return 2
    return 3


def is_weekend(dt):
    # Friday and Saturday nights; past-midnight hours count as the previous day
    return int((dt - datetime.timedelta(hours=5)).weekday() in (4, 5))


def encode(gender, age, is_smiling, dt):
    """Turn one detection into {feature name: integer category}."""
    return {
        'gender': GENDER_LIST.index(gender),
        'age': AGE_BUCKETS.index(age),
        'is_smiling': int(bool(is_smiling)),
        'time_of_day': time_of_day(dt),
        'is_weekend': is_weekend(dt),
    }
