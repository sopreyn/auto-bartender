"""Train the drink recommender on logged orders.

Usage:
    python train.py                     # reads orders.csv, writes drink_model.joblib
    python train.py --min-confidence 0.7

Prints leave-one-out accuracy for the model against a "most popular drink"
baseline, plus face-only and time-only variants, so you can see which signals
actually help before trusting the model.
"""
import argparse
import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.naive_bayes import CategoricalNB

from features import FACE_FEATURES, FEATURES, TIME_FEATURES, encode


def load_orders(path, min_confidence):
    df = pd.read_csv(path)
    before = len(df)
    df = df[(df['gender_confidence'] >= min_confidence) & (df['age_confidence'] >= min_confidence)]
    if len(df) < before:
        print(f"Dropped {before - len(df)} of {before} orders below confidence {min_confidence}")
    rows = [
        encode(r.gender, r.age, r.is_smiling, datetime.datetime.fromisoformat(r.timestamp))
        for r in df.itertuples()
    ]
    return pd.DataFrame(rows, columns=list(FEATURES)), df['drink'].to_numpy()


def make_model(columns):
    return CategoricalNB(alpha=1.0, min_categories=[FEATURES[c] for c in columns])


def leave_one_out(X, y, columns):
    """Return (top-1, top-3) accuracy, holding out each order once."""
    X = X[columns].to_numpy()
    top1 = top3 = 0
    for i in range(len(y)):
        mask = np.arange(len(y)) != i
        model = make_model(columns).fit(X[mask], y[mask])
        probs = model.predict_proba(X[i:i + 1])[0]
        ranked = model.classes_[np.argsort(probs)[::-1]]
        top1 += ranked[0] == y[i]
        top3 += y[i] in ranked[:3]
    return top1 / len(y), top3 / len(y)


def baseline(y):
    """Always guess the most popular drinks (from the other orders)."""
    top1 = top3 = 0
    for i in range(len(y)):
        counts = pd.Series(np.delete(y, i)).value_counts()
        top1 += counts.index[0] == y[i]
        top3 += y[i] in counts.index[:3]
    return top1 / len(y), top3 / len(y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--orders', default='orders.csv')
    parser.add_argument('--out', default='drink_model.joblib')
    parser.add_argument('--min-confidence', type=float, default=0.0,
                        help='drop orders where age or gender confidence is below this')
    args = parser.parse_args()

    X, y = load_orders(args.orders, args.min_confidence)
    print(f"{len(y)} orders\n{pd.Series(y).value_counts().to_string()}\n")
    if len(y) < 2:
        print("Need at least 2 orders to train.")
        return

    print(f"{'leave-one-out':<28}{'top-1':>8}{'top-3':>8}")
    for name, (t1, t3) in [
        ('most popular (baseline)', baseline(y)),
        ('face only', leave_one_out(X, y, FACE_FEATURES)),
        ('time only', leave_one_out(X, y, TIME_FEATURES)),
        ('face + time', leave_one_out(X, y, list(FEATURES))),
    ]:
        print(f"{name:<28}{t1:>8.0%}{t3:>8.0%}")

    model = make_model(list(FEATURES)).fit(X.to_numpy(), y)
    joblib.dump({'model': model, 'columns': list(FEATURES)}, args.out)
    print(f"\nSaved face + time model to {args.out}")


if __name__ == '__main__':
    main()
