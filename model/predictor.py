def predict(features):
    """Simple placeholder predictor.

    Args:
        features (list): list of numeric features (we use first one)

    Returns:
        dict: label and score
    """
    f = features[0] if features else 0.0
    # simple rule: threshold at 0.5
    score = max(0.0, min(1.0, float(f)))
    label = 'Approved' if score > 0.5 else 'Rejected'
    return {'label': label, 'score': round(score, 2)}
