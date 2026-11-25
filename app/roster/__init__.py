"""Public facade for late-relation supplements and available rosters."""
from app.modules.roster import (  # noqa: F401
    DSU,
    build_roster,
    case_roster,
    identifier,
    normalize_relation,
    resolve_case,
    roster_matches_token,
    roster_signature,
    sorted_ids,
)
from app.review.service import (  # noqa: F401
    add_link,
    add_links,
    add_relation,
    add_relations,
    add_supplement,
    add_supplements,
    append_relation,
    append_relations,
    record_relation,
    record_relations,
    supplement,
    supplement_relation,
    supplement_relations,
)
from app.review.store import Store  # noqa: F401


def available_roster(source=None, second=None, supplements=None):
    """Return a roster from either ``(report, supplements)`` or ``(store, id)``."""
    if source is not None and second is not None and hasattr(source, 'load') and isinstance(second, str):
        loaded = source.load(second)
        if supplements is not None:
            return build_roster(loaded['report'], supplements)
        return loaded['roster']
    if supplements is None:
        supplements = second
    return build_roster(source, supplements)


def current_roster(store, run_id):
    return store.load(run_id)['roster']


def get_roster(source, run_id=None):
    if run_id is not None and hasattr(source, 'load'):
        return source.load(run_id)['roster']
    return build_roster(source, run_id)


class RosterService:
    def __init__(self, store):
        self.store = store

    def supplement(self, run_id, values=None, *args, **kwargs):
        return supplement(self.store, run_id, values, *args, **kwargs)

    add_relation = supplement
    add_supplement = supplement
    record_relation = supplement
    append_relation = supplement

    def get(self, run_id):
        return self.store.load(run_id)['roster']

    get_roster = get
    get_available = get
    available = get
    current = get
    current_roster = get
    list_available = get


class SupplementService(RosterService):
    pass


class RelationService(RosterService):
    pass


RosterStore = Store
SupplementStore = Store

__all__ = [
    'DSU', 'Store', 'RosterStore', 'SupplementStore', 'RosterService',
    'SupplementService', 'add_link',
    'add_links', 'add_relation', 'add_relations', 'add_supplement',
    'add_supplements', 'append_relation', 'append_relations',
    'available_roster', 'build_roster', 'case_roster', 'current_roster',
    'get_roster', 'identifier', 'normalize_relation', 'record_relation',
    'record_relations', 'resolve_case', 'roster_matches_token',
    'roster_signature', 'sorted_ids', 'supplement', 'supplement_relation',
    'supplement_relations',
]
