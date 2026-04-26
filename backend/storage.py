"""
JSON-based persistence for enriched leads, scores, pain points, and outreach.

Layout:
  data/
    index.json          ← lightweight index (id, name, company, score, grade)
    leads/
      {id}.json         ← full record per lead
"""
from __future__ import annotations
import json
import pathlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

_DATA_DIR   = pathlib.Path(__file__).parent.parent / "data" / "leads"
_INDEX_PATH = _DATA_DIR.parent / "index.json"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_lead(
    lead_info: Dict[str, Any],
    enrichment: Dict[str, Any],
    scores: Dict[str, Any],
    pain_points: List[Dict[str, Any]],
    outreach: Dict[str, Any],
    lead_id: Optional[str] = None,
) -> str:
    """
    Persist the full pipeline output.
    lead_id: use the test-data id when provided (idempotent re-runs overwrite the file);
             otherwise generate a fresh UUID.
    Returns the lead_id used.
    """
    _ensure_dir()
    if not lead_id:
        lead_id = str(uuid.uuid4())

    record = {
        "id":          lead_id,
        "created_at":  datetime.utcnow().isoformat() + "Z",
        "lead_info":   lead_info,
        "enrichment":  enrichment,
        "scores":      scores,
        "pain_points": pain_points,
        "outreach":    outreach,
    }
    (_DATA_DIR / f"{lead_id}.json").write_text(
        json.dumps(record, indent=2, default=str), encoding="utf-8"
    )
    _update_index(lead_id, lead_info, scores)
    return lead_id


def _update_index(lead_id: str, lead_info: Dict[str, Any], scores: Dict[str, Any]) -> None:
    index: List[Dict] = []
    if _INDEX_PATH.exists():
        try:
            index = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            index = []

    # Replace existing entry with same id (idempotent re-run) instead of appending
    index = [e for e in index if e.get("id") != lead_id]
    index.insert(0, {
        "id":         lead_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "name":       lead_info.get("name"),
        "company":    lead_info.get("company"),
        "city":       lead_info.get("city"),
        "state":      lead_info.get("state"),
        "lead_score": scores.get("lead_score", {}).get("score"),
        "grade":      scores.get("lead_score", {}).get("grade"),
    })
    _INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")


def get_lead(lead_id: str) -> Optional[Dict[str, Any]]:
    path = _DATA_DIR / f"{lead_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def list_leads() -> List[Dict[str, Any]]:
    if not _INDEX_PATH.exists():
        return []
    try:
        return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
