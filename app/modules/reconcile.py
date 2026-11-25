from collections import Counter


def balance(intake, cases):
    accounted = intake['accepted'] + intake['rejected'] + intake['blank'] + intake['repeated']
    status = Counter(case['status'] for case in cases)
    ready = status.pop('READY', 0)
    observed = sum(len(case['records']) for case in cases)
    return dict(input=intake['input'], accepted=intake['accepted'], isolated=intake['rejected'],
                ignored=intake['blank'] + intake['repeated'], accounted=accounted,
                balanced=accounted == intake['input'] and observed == intake['accepted'],
                ready=ready, pending=len(cases)-ready, issues=dict(sorted(status.items())),
                releasable=bool(cases) and ready==len(cases) and not intake['rejected'] and accounted==intake['input'] and observed==intake['accepted'])
