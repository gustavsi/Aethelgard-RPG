"""
Living hub schedule (PRD D1) — Oakhaven options by time-of-day.
"""
from __future__ import annotations

from typing import Dict, Tuple

from engine.feature_flags import FLAGS


def oakhaven_menu_options(state) -> Dict[str, str]:
    """Return leader menu options for Oakhaven hub."""
    time_of_day = state.get_flag("time_of_day", "Dia") if state else "Dia"
    base = {
        "1": "Visitar a Taverna do Javali Saltitante",
        "2": "Visitar a Forja de Garrett",
        "3": "Falar com o Ancião Alistair",
        "4": "Salvar Jogo",
        "5": "Gerenciar Equipamentos e Status",
        "6": "Viajar para as Cavernas Sussurrantes (Seguir a Missão)",
    }
    if not FLAGS.content_systems:
        return base

    if time_of_day == "Noite":
        base["2"] = "⚒️ Forja de Garrett (fechada à noite)"
        base["7"] = "📜 Quadro de Rumores (tocha fraca)"
        base["1"] = "🍺 Taverna (aberta até tarde)"
    else:
        base["7"] = "📜 Quadro de Rumores da Praça"

    base["8"] = "📖 Códex dos Ecos"

    # Schedule flavor for elder
    if time_of_day == "Noite":
        base["3"] = "Falar com o Ancião (pode estar descansando)"

    return base


def is_forge_open(state) -> bool:
    if not FLAGS.content_systems:
        return True
    return state.get_flag("time_of_day", "Dia") != "Noite"


def schedule_blurb(state) -> str:
    t = state.get_flag("time_of_day", "Dia")
    w = state.get_flag("weather", "Ensolarado")
    if t == "Noite":
        return f"🌙 Noite em Oakhaven ({w}). A forja dorme; a taverna ainda canta."
    return f"☀️ Dia em Oakhaven ({w}). Mercadores e o mural de rumores estão ativos."
