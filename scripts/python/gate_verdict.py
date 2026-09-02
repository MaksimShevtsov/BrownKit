#!/usr/bin/env python3
"""Deterministic verdict for the `/gate` hook (before_implement).

Reads the `/assess` evidence tree for one capability and classifies
PASS | WARN | BLOCK | NOT-ASSESSED using the thresholds that used to live
in commands/gate.md Phase 3. The LLM matches the feature to a capability;
this script is the verdict. Its `verdict_line` must be quoted verbatim.

Stdlib only. JSON on stdout; nothing is written to disk.

Exit codes:
   0  PASS
   1  BLOCK
   2  NOT-ASSESSED (assess not run, risk map or vulnerability catalog
                    missing/unreadable, capability absent from the map,
                    malformed --capability)
   3  WARN
"""

from __future__ import annotations

import re
from pathlib import Path

BC_ID = re.compile(r"^BC-\d{3}$")

EXIT_CODES = {"PASS": 0, "WARN": 3, "BLOCK": 1, "NOT-ASSESSED": 2}

REVIEWED_STATUSES = {"false_positive", "mitigated_elsewhere", "accepted_risk"}

SENTINELS = ("unknown", "partial")


def load_json(path: Path):
    """(data, None) or (None, error). Never raises."""
    import json
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as e:
        return None, f"{path}: {e.strerror or e}"
    except json.JSONDecodeError as e:
        return None, f"{path}: invalid JSON ({e.msg} at line {e.lineno})"


def _entries(data, keys):
    """Coerce a script input to a list: a bare list, or the first list-valued
    `keys` field of a wrapper object. None when the shape is unrecognized."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
    return None


def find_capability(risk_map, cap):
    for entry in _entries(risk_map, ("capabilities", "entries")) or []:
        if isinstance(entry, dict) and entry.get("id") == cap:
            return entry
    return None


def composite_of(entry):
    """Unified composite as a float in [0, 1], or the 'unknown'/'partial'
    sentinel. Never fabricates a number for an absent or malformed value
    (bools and out-of-range values are malformed, per the schema's
    composite_numeric definition)."""
    node = None
    unified = entry.get("unified")
    if isinstance(unified, dict):
        node = unified.get("composite")
    if node is None:
        risk_score = entry.get("risk_score")
        if isinstance(risk_score, dict):
            node = risk_score.get("unified_composite")
    if isinstance(node, str) and node.lower() in SENTINELS:
        return node.lower()
    if (isinstance(node, (int, float)) and not isinstance(node, bool)
            and 0 <= node <= 1):
        return float(node)
    return "unknown"


def split_vulnerabilities(catalog, cap):
    """(confirmed_open, probable_open, reviewed) for the capability.

    Entries whose `status` is a review marker count as reviewed, not open;
    an absent `status` means open. `Potential` findings are neither — they
    are not a verdict trigger."""
    confirmed, probable, reviewed = [], [], []
    for v in _entries(catalog, ("vulnerabilities", "entries", "items")) or []:
        if not isinstance(v, dict) or v.get("capability") != cap:
            continue
        status = str(v.get("status") or "open").lower()
        if status in REVIEWED_STATUSES:
            reviewed.append(v)
            continue
        classification = str(v.get("classification", "")).lower()
        if classification == "confirmed":
            confirmed.append(v)
        elif classification == "probable":
            probable.append(v)
    return confirmed, probable, reviewed


_L1_HEADER = re.compile(r"^BC-\d{3}:.+$", re.MULTILINE)
_CRITICALITY = re.compile(r"^\s*Criticality:\s*(low|medium|high)\b",
                          re.IGNORECASE | re.MULTILINE)


def criticality_of(evidence: Path, cap: str):
    """Criticality from the BC's Security Context block in domain-model.md
    (rendering template: discover.md D7), or None when the file, the
    section, or the field is absent. L2 headers are indented and carry a
    `-NN` suffix, so the `^BC-\\d{3}:` anchor matches L1 sections only."""
    domain_model = evidence / "discovery/domain-model.md"
    if not domain_model.exists():
        return None
    text = domain_model.read_text(encoding="utf-8", errors="ignore")
    start = None
    for header in _L1_HEADER.finditer(text):
        if text.startswith(cap + ":", header.start()):
            start = header.start()
            break
    if start is None:
        return None
    nxt = _L1_HEADER.search(text, start + 1)
    section = text[start: nxt.start() if nxt else len(text)]
    match = _CRITICALITY.search(section)
    return match.group(1).lower() if match else None


def posture_of(qa_risk, cap):
    """QA posture for the capability, or None when absent."""
    if isinstance(qa_risk, dict) and isinstance(qa_risk.get(cap), dict):
        return qa_risk[cap].get("posture")
    for entry in _entries(qa_risk, ("capabilities", "entries")) or []:
        if isinstance(entry, dict) and cap in (entry.get("capability"),
                                               entry.get("id")):
            return entry.get("posture")
    return None


def control_gaps_for(control_map, cap, scope):
    """Gaps of absent/inconsistent controls on scoped L2 operations.

    scope is a set of L2 ids, or None for 'all of the capability's L2s'
    (conservative superset). Returns None when the file is missing or its
    shape is unrecognized — absence is a signal, never a silent zero."""
    entries = _entries(control_map, ("controls", "entries", "items"))
    if entries is None:
        return None
    gaps = []
    for control in entries:
        if not isinstance(control, dict) or control.get("capability") != cap:
            continue
        if (control.get("present") is not False
                and control.get("consistently_applied") is not False):
            continue
        for gap in control.get("gaps") or []:
            if not isinstance(gap, dict):
                continue
            if scope is not None and gap.get("l2") not in scope:
                continue
            gaps.append({
                "family": control.get("control_family"),
                "l2": gap.get("l2"),
                "operation": gap.get("operation"),
                "issue": gap.get("issue"),
            })
    return gaps


def _is_blocked_entry(entry):
    severity = str(entry.get("severity", "")).lower()
    if severity in ("blocked", "blocks"):
        return True
    kind = str(entry.get("type") or entry.get("kind") or "").lower()
    text = " ".join(str(entry.get(k) or "")
                    for k in ("finding", "issue", "description")).lower()
    return kind == "testability" and "block" in text


def blocked_testability_for(qa_gaps, cap, scope):
    """Blocked testability findings attributed to the capability on scoped
    L2s. Returns None when qa-gaps.json is missing or unrecognized, or when
    no entry carries capability/l2 attribution at all."""
    entries = _entries(qa_gaps, ("gaps", "findings", "items"))
    if entries is None:
        return None
    attributed = False
    blocked = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        l2 = str(entry.get("l2") or "")
        entry_cap = str(entry.get("capability") or "")
        if entry_cap == cap or l2 == cap or l2.startswith(cap + "-"):
            attributed = True
            if scope is not None and l2 and l2 not in scope:
                continue
            if _is_blocked_entry(entry):
                blocked.append(entry)
    if not attributed and entries:
        return None
    return blocked


def _iter_threats(node, category=None):
    """Yield (threat_dict, category) for every dict carrying a
    likelihood_hint, whatever the surrounding file shape."""
    if isinstance(node, dict):
        cat = node.get("category") or category
        if "likelihood_hint" in node:
            yield node, cat
        else:
            for value in node.values():
                yield from _iter_threats(value, cat)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_threats(value, category)


def _mitigated_ids(control_map):
    mitigated = set()
    for control in _entries(control_map,
                            ("controls", "entries", "items")) or []:
        if isinstance(control, dict):
            mitigated.update(control.get("mitigates") or [])
    return mitigated


def high_likelihood_unmitigated(threats, control_map):
    """High-likelihood threats no control claims to mitigate. Display
    detail only — they already feed the composite."""
    if threats is None:
        return []
    mitigated = _mitigated_ids(control_map)
    out = []
    for threat, category in _iter_threats(threats):
        if str(threat.get("likelihood_hint", "")).lower() != "high":
            continue
        if threat.get("id") in mitigated:
            continue
        out.append({
            "id": threat.get("id"),
            "category": category,
            "description": threat.get("description", ""),
        })
    return out
