"""Suggest fixes for typos of big provider domains (never applied silently)."""

from .data import KNOWN_LEGIT_NEIGHBOURS, PROVIDERS, TYPO_MAP

_FUZZY_MIN_LEN = 9  # shorter targets only match through the explicit map


def edit_distance(a, b):
    """Damerau-Levenshtein distance (optimal string alignment)."""
    rows = len(a) + 1
    cols = len(b) + 1
    dist = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        dist[i][0] = i
    for j in range(cols):
        dist[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dist[i][j] = min(
                dist[i - 1][j] + 1,
                dist[i][j - 1] + 1,
                dist[i - 1][j - 1] + cost,
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                dist[i][j] = min(dist[i][j], dist[i - 2][j - 2] + 1)
    return dist[-1][-1]


def _limit(target):
    return 2 if len(target) >= 12 else 1


def suggest_domain(domain):
    """Return the provider domain ``domain`` probably meant, or None."""
    domain = domain.lower()
    if domain in PROVIDERS or domain in KNOWN_LEGIT_NEIGHBOURS:
        return None
    if domain in TYPO_MAP:
        return TYPO_MAP[domain]
    best = None
    for target in PROVIDERS:
        if len(target) < _FUZZY_MIN_LEN or abs(len(target) - len(domain)) > 2:
            continue
        distance = edit_distance(domain, target)
        if distance <= _limit(target) and (best is None or distance < best[0]):
            best = (distance, target)
    return best[1] if best else None
