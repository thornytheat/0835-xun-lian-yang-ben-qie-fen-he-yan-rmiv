from collections import defaultdict

from app.modules.roster import (  # noqa: F401
    DSU,
    DisjointSet,
    UnionFind,
    build_roster,
    case_roster,
    normalize_relation,
    roster_from_records,
)


def case_groups(rows):
    groups = defaultdict(list)
    for row in sorted(rows,key=lambda r:(r['case'],r['record'])):
        groups[row['case']].append(row)
    return groups.items()


def transitive_groups(initial_groups=(), relations=()):
    """Return connected groups after adding late relations."""
    dsu = DSU()
    for group in initial_groups or ():
        ids = list(group)
        for value in ids:
            dsu.add(value)
        if ids:
            first = ids[0]
            for value in ids[1:]:
                dsu.union(first, value)
    for relation in relations or ():
        if isinstance(relation, dict):
            a = relation.get('a', relation.get('left'))
            b = relation.get('b', relation.get('right'))
        else:
            a, b = relation
        dsu.union(a, b)
    return dsu.groups()


apply_relations = transitive_groups
supplement_groups = transitive_groups
available_roster = build_roster
