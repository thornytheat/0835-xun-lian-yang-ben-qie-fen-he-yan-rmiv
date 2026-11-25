from app.business import measured


def compute(data):
    from collections import defaultdict
    records,links,rule = data
    parents = {key:key for key in records}

    def find(key):
        while parents[key]!=key:
            parents[key]=parents[parents[key]]
            key=parents[key]
        return key

    def merge(a,b):
        left,right = sorted((find(a),find(b)))
        parents[right]=left

    seen = {}
    for key,row in sorted(records.items()):
        for match in ('entity','fingerprint'):
            merge(key,seen.setdefault((match,row[match]),key))
    for a,b in links:
        merge(a,b)
    groups = defaultdict(list)
    for key in sorted(records):
        groups[find(key)].append(key)
    result = {'train':[],'evaluation':[],'quarantined':[],'groups':list(groups.values())}
    for group in groups.values():
        sides = {1 if records[key]['day']<rule['day'] else 2 for key in group}
        locks = {records[key]['split_code'] for key in group}-{0}
        if len(sides)>1 or locks-sides:
            result['quarantined'].extend(group)
        else:
            result['train' if 1 in sides else 'evaluation'].extend(group)
    for key in ('train','evaluation','quarantined'):
        result[key].sort()
    return measured(len(result['evaluation']),rule['split_code'],'条',result,bool(result['quarantined']))
