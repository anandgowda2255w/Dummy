"""
machine_resolver.py — Machine Name ↔ ID resolution layer.

Converts user-facing machine names / aliases to machine IDs before any backend call.
Backend functions always receive machine IDs; this layer is a front-end
translation step and never touches analytics function signatures.

Alias table covers the spec-defined names plus common shorthands so operators
can type "Press", "Lathe", "Grinder", etc. and still get a unique match.

Usage:
    from llm.machine_resolver import get_resolver
    resolver = get_resolver()
    machine_id = resolver.resolve("hydraulic press")   # → "M009"
    name       = resolver.get_display_name("M009")     # → "Hydraulic Press (M009)"
"""

import re
from analytics.analytics_engine import get_all_machines


# ---------------------------------------------------------------------------
# Static alias table
# Maps alias (lowercase) → machine ID
# Populated from spec §4 plus sensible variants.
# DB-loaded names are also added dynamically at runtime.
# ---------------------------------------------------------------------------
STATIC_ALIASES: dict[str, str] = {
    # M001 — CNC Lathe 1
    "cnc lathe 1":       "M001",
    "cnc lathe1":        "M001",
    "cnc machine 1":     "M001",
    "cnc1":              "M001",
    "cnc 1":             "M001",
    "lathe 1":           "M001",

    # M002 — CNC Lathe 2
    "cnc lathe 2":       "M002",
    "cnc lathe2":        "M002",
    "cnc machine 2":     "M002",
    "cnc2":              "M002",
    "cnc 2":             "M002",
    "lathe 2":           "M002",

    # M003 — Hydraulic Lathe
    "hydraulic lathe":   "M003",
    "hydraulic lathe 1": "M003",

    # M004 — Precision Lathe
    "precision lathe":   "M004",
    "precision lathe 1": "M004",

    # M005 — Drill Press 1
    "drill press 1":     "M005",
    "drill press1":      "M005",
    "drill machine 1":   "M005",
    "drill 1":           "M005",

    # M006 — Drill Press 2
    "drill press 2":     "M006",
    "drill press2":      "M006",
    "drill machine 2":   "M006",
    "drill 2":           "M006",

    # M007 — Milling Center
    "milling center":    "M007",
    "milling machine 1": "M007",
    "milling machine":   "M007",
    "milling":           "M007",
    "mill":              "M007",

    # M008 — Surface Grinder
    "surface grinder":   "M008",
    "grinding machine 1":"M008",
    "grinding machine":  "M008",
    "grinder":           "M008",
    "surface grinder 1": "M008",

    # M009 — Hydraulic Press
    "hydraulic press":   "M009",
    "press machine 1":   "M009",
    "press machine":     "M009",
    "press":             "M009",

    # M010 — Assembly Line
    "assembly line":     "M010",
    "assembly machine 1":"M010",
    "assembly machine":  "M010",
    "assembly":          "M010",
}


class MachineResolver:
    """Lazy-loaded, case-insensitive machine name/alias/ID resolver."""

    def __init__(self):
        self._machines: list[dict] | None = None
        self._alias_map: dict[str, str] | None = None   # lowercase alias → machine_id

    def _load(self):
        if self._machines is not None:
            return
        self._machines = get_all_machines()   # [{machine_id, machine_name}, ...]

        # Build alias map: static aliases + DB names + IDs
        alias = dict(STATIC_ALIASES)  # start from static table
        for m in self._machines:
            mid  = m["machine_id"]
            name = m["machine_name"].lower()
            alias[name] = mid                        # e.g. "hydraulic press" → M009
            alias[mid.lower()] = mid                 # e.g. "m009" → M009
        self._alias_map = alias

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def all_machines(self) -> list[dict]:
        """Return [{machine_id, machine_name}, ...] from DB."""
        self._load()
        return self._machines

    def _normalise_candidate(self, raw: str) -> str:
        """Normalise user text for machine matching."""
        value = re.sub(r"\bmachine\b", " ", raw or "", flags=re.IGNORECASE)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def resolve(self, raw: str) -> str | None:
        """
        Resolve a raw string to a canonical machine ID.
        Tries (in order):
          1. Exact ID match (M001 … M010)
          2. Exact alias / DB-name match
          3. Partial fuzzy match (all words present in name)
        Returns None if no unique match.
        """
        if not raw:
            return None
        self._load()
        key = self._normalise_candidate(raw).lower()

        # 1. Alias / exact match
        if key in self._alias_map:
            return self._alias_map[key]

        # 2. Fuzzy: all words in raw appear in some machine name
        words = key.split()
        if not words:
            return None
        candidates = []
        for m in self._machines:
            name_lower = m["machine_name"].lower()
            if all(w in name_lower for w in words):
                candidates.append(m)

        # Also check aliases
        if not candidates:
            matched_ids = set()
            for alias_key, mid in self._alias_map.items():
                if all(w in alias_key for w in words):
                    matched_ids.add(mid)
            if len(matched_ids) == 1:
                return matched_ids.pop()
            if len(matched_ids) > 1:
                return None  # ambiguous

        if len(candidates) == 1:
            return candidates[0]["machine_id"]

        return None  # ambiguous or not found

    def get_ambiguous_matches(self, raw: str) -> list[dict]:
        """
        Return all machines that could match raw (for the 'multiple match' prompt).
        """
        if not raw:
            return []
        self._load()
        key = self._normalise_candidate(raw).lower()
        words = key.split()
        if not words:
            return []

        seen_ids = set()
        results  = []

        # From DB names
        for m in self._machines:
            if all(w in m["machine_name"].lower() for w in words):
                if m["machine_id"] not in seen_ids:
                    seen_ids.add(m["machine_id"])
                    results.append(m)

        # From alias map
        for alias_key, mid in self._alias_map.items():
            if all(w in alias_key for w in words) and mid not in seen_ids:
                seen_ids.add(mid)
                # Find full record
                for m in self._machines:
                    if m["machine_id"] == mid:
                        results.append(m)
                        break

        return results

    def get_display_name(self, machine_id: str) -> str:
        """Return 'Machine Name (MID)' for reports."""
        self._load()
        for m in self._machines:
            if m["machine_id"] == machine_id:
                return f"{m['machine_name']} ({machine_id})"
        return machine_id

    def get_name(self, machine_id: str) -> str:
        """Return just the machine name."""
        self._load()
        for m in self._machines:
            if m["machine_id"] == machine_id:
                return m["machine_name"]
        return machine_id

    def id_from_name_or_id(self, raw: str) -> tuple[str | None, list[dict]]:
        """
        Returns (machine_id, []) on unique match,
                (None, [candidates]) on ambiguous,
                (None, []) on no match.
        """
        mid = self.resolve(raw)
        if mid:
            return mid, []
        candidates = self.get_ambiguous_matches(raw)
        return None, candidates


# Singleton
_resolver: MachineResolver | None = None


def get_resolver() -> MachineResolver:
    global _resolver
    if _resolver is None:
        _resolver = MachineResolver()
    return _resolver
