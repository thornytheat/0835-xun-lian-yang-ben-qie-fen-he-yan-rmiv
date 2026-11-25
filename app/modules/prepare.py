from app.business import DomainIssue, by_kind, prepared, single


def prepare(rows):
    rule = single(rows,'rule')
    samples = by_kind(rows,'record')
    records = {r['sample']:r for r in samples}
    if not records or len(records)!=len(samples) or any(not r['sample'] or not r['entity'] or not r['fingerprint'] or r['split_code']>2 for r in samples):
        raise DomainIssue('INVALID_SAMPLE_REGISTRY')
    links = []
    for row in by_kind(rows,'duplicate'):
        a,b = row['sample'],row['entity']
        if a not in records or b not in records or a==b:
            raise DomainIssue('UNKNOWN_SAMPLE')
        links.append((a,b))
    return prepared(len(samples),{'cutoff':rule['day'],'confirmed_near_duplicates':len(links)},(records,links,rule))
