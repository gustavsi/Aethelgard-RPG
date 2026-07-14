"""
Codex of Echoes (PRD C1) — party-shared discovery journal.
"""
from __future__ import annotations

from typing import Any, Dict, List

from engine.feature_flags import FLAGS
from engine import telemetry

# entry_id -> (title, body, unlock_flag)
CODEX_CATALOG: Dict[str, tuple] = {
    "drogg": (
        "Drogg, o Ogro",
        "Uma criatura temerosa sob a fúria. Poupar Drogg grava uma dívida de vida.",
        "poupou_ogro",
    ),
    "zix": (
        "Zix, o Goblin",
        "Ferido nas cavernas. Ajuda gera atalhos e gratidão inesperada.",
        "goblin_ajudado",
    ),
    "malakar": (
        "Lorde Malakar",
        "Não era apenas um tirano — era um dique. Sua morte soltou o que continha.",
        "malakar_derrotado",
    ),
    "vesper": (
        "Vesper, Arauto do Vazio",
        "Rival de máscara cinza. Estuda a party e adapta o próximo golpe.",
        "vesper_gelido_confrontada",
    ),
    "lacre": (
        "Lacre Sombrio",
        "Relíquia que sussurra. Aceitá-la marca a party com o Vazio.",
        "lacre_sombrio",
    ),
    "oakhaven_siege": (
        "Cerco de Oakhaven",
        "Três frentes. Uma cidade. A noite em que Oakhaven não caiu — ou quase.",
        "oakhaven_defendida",
    ),
    "ulfgar": (
        "Ulfgar, o Cego",
        "Bárbaro do gelo cujo olhar foi tomado pelo Vazio — e devolvido pela party.",
        "ulfgar_ajudado",
    ),
    "corruption": (
        "Corrupção do Vazio",
        "Poder e preço. Quanto mais a party bebe, mais o Vazio bebe de volta.",
        None,  # unlocked when corruption > 0
    ),
}


def _unlocked_ids(state) -> List[str]:
    ids = []
    for eid, (_t, _b, flag) in CODEX_CATALOG.items():
        if flag is None:
            try:
                from engine.party_meta import ensure_meta
                if ensure_meta(state).get("corruption", 0) > 0:
                    ids.append(eid)
            except Exception:
                pass
            continue
        if state.get_flag(flag) or state.get_flag(
            {"poupou_ogro": "ogro_poupado", "goblin_ajudado": "ajudou_goblin"}.get(flag, flag)
        ):
            ids.append(eid)
    # Also check aliases
    if state.get_flag("ogro_poupado") and "drogg" not in ids:
        ids.append("drogg")
    if state.get_flag("ajudou_goblin") and "zix" not in ids:
        ids.append("zix")
    return sorted(set(ids))


def public_view(state) -> Dict[str, Any]:
    if not FLAGS.content_systems:
        return {"entries": [], "unlocked": 0, "total": len(CODEX_CATALOG)}
    unlocked = _unlocked_ids(state)
    entries = []
    for eid in unlocked:
        title, body, _f = CODEX_CATALOG[eid]
        entries.append({"id": eid, "title": title, "body": body})
    return {
        "entries": entries,
        "unlocked": len(entries),
        "total": len(CODEX_CATALOG),
    }


def try_unlock_from_flags(state) -> List[str]:
    """Returns newly unlocked ids this call (for narrative pings)."""
    if not FLAGS.content_systems:
        return []
    meta = getattr(state, "party_meta", None) or {}
    known = set(meta.get("codex_unlocked") or [])
    current = set(_unlocked_ids(state))
    new = sorted(current - known)
    if new:
        meta = dict(meta) if meta else {}
        meta["codex_unlocked"] = sorted(current)
        state.party_meta = meta if hasattr(state, "party_meta") else meta
        # store on party_meta properly
        try:
            from engine.party_meta import ensure_meta
            m = ensure_meta(state)
            m["codex_unlocked"] = sorted(current)
        except Exception:
            pass
        for eid in new:
            telemetry.track("codex_unlock", entry=eid)
    return new


def show_codex(world) -> None:
    from engine.world import clear_screen, typewriter, print_centered, press_any_key

    clear_screen()
    print_centered("=== CÓDEX DOS ECOS ===", None)
    view = public_view(world.state)
    if not view["entries"]:
        typewriter("Páginas em branco. O mundo ainda não se revelou a vocês.", 0.03)
        press_any_key()
        return
    typewriter(f"Entradas: {view['unlocked']}/{view['total']}\n", 0.02)
    for e in view["entries"]:
        typewriter(f"• {e['title']}", 0.02)
        typewriter(f"  {e['body']}\n", 0.02)
    press_any_key()
