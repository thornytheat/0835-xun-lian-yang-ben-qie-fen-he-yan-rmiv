from app.business import decision


def policy(result):
    return decision(result,'CROSS_CUTOFF_LEAKAGE' if result['flag'] else None)
