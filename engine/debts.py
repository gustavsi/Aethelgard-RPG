"""
Debt Ledger — named favors and spared lives (PRD F1, unified with Mercy).

Statuses: open | closed | defaulted
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Catalog of known debts (content hooks for later chapters)
DEBT_CATALOG: Dict[str, Dict[str, str]] = {
    "drogg_spared": {
        "title": "Vida de Drogg",
        "source": "Ogre poupado na cabana",
    },
    "zix_aided": {
        "title": "Dívida de Zix",
        "source": "Goblin ferido ajudado nas cavernas",
    },
    "millhaven_child": {
        "title": "Promessa de Millhaven",
        "source": "Criança purificada em Millhaven",
    },
}


def empty_debts() -> List[Dict[str, Any]]:
    return []


def find_debt(debts: List[Dict[str, Any]], debt_id: str) -> Optional[Dict[str, Any]]:
    for d in debts:
        if d.get("id") == debt_id:
            return d
    return None


def grant_debt(
    debts: List[Dict[str, Any]],
    debt_id: str,
    *,
    chapter: int = 1,
    title: Optional[str] = None,
    source: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Add debt if not already present. Returns entry or None if duplicate."""
    if find_debt(debts, debt_id):
        return None
    cat = DEBT_CATALOG.get(debt_id, {})
    entry = {
        "id": debt_id,
        "title": title or cat.get("title", debt_id),
        "source": source or cat.get("source", ""),
        "status": "open",
        "created_chapter": chapter,
    }
    debts.append(entry)
    return entry


def close_debt(debts: List[Dict[str, Any]], debt_id: str, status: str = "closed") -> bool:
    d = find_debt(debts, debt_id)
    if not d:
        return False
    d["status"] = status
    return True


def normalize_debts(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        out.append(
            {
                "id": str(item["id"]),
                "title": str(item.get("title") or item["id"]),
                "source": str(item.get("source") or ""),
                "status": str(item.get("status") or "open"),
                "created_chapter": int(item.get("created_chapter") or 1),
            }
        )
    return out


def debts_public_view(debts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list(debts)
