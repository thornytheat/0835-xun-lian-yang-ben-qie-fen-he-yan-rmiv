from collections import defaultdict


def case_groups(rows):
    groups = defaultdict(list)
    for row in sorted(rows,key=lambda r:(r['case'],r['record'])):
        groups[row['case']].append(row)
    return groups.items()
