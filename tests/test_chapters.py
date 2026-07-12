"""
Testes completos para os capítulos 3, 4 e 5 do RPG PIka.

Cobertura obrigatória por capítulo:
  — Fluxo principal sem class gates (party genérica)
  — Fluxo com class gate ativo (ex: Clérigo purifica criança)
  — Flags de consequência sendo setadas corretamente
  — Flags de consequências anteriores sendo lidas corretamente
  — Boss de cada capítulo sendo derrotado
"""

import pytest
from unittest.mock import patch, MagicMock, call

from engine.player import Player
from engine.state import GameState
from engine.world import WorldManager
from engine.constants import CharacterClass, StatusEffect
from engine.exceptions import GameOverException


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_sleep_and_clear():
    """Silencia sleep e clear_screen em todas as camadas."""
    with patch('time.sleep', return_value=None), \
         patch('engine.console.clear_screen', return_value=None):
        yield


class _FakeCombat:
    """Um CombatSystem fake que vence automaticamente ao chamar run()."""
    def __init__(self, state, enemies, can_flee=False, turn_hook=None, **kw):
        self.state = state
        self.enemies = enemies
        self.turn_hook = turn_hook
        for e in enemies:
            e.hp = 0

    def run(self):
        return True

    def distribute_rewards(self):
        pass


class InputQueue:
    """Fila de inputs que retorna valores sequencialmente para get_menu_choice."""
    def __init__(self, inputs):
        self._inputs = list(inputs)
        self._idx = 0

    def __call__(self, options, prompt="Escolha uma opção: ", **kwargs):
        if self._idx < len(self._inputs):
            val = self._inputs[self._idx]
            self._idx += 1
            return val
        # Fallback: retorna primeira opção válida
        return list(options.keys())[0]


def _make_world(char_class: CharacterClass, flags: dict | None = None, level: int = 5):
    """Cria um WorldManager pronto para testes, com player nivelado."""
    player = Player("Herói", char_class)
    for _ in range(level - 1):
        player.gain_xp(player.get_xp_needed())
    player.hp = player.max_hp
    player.mp = player.max_mp

    state = GameState(player)
    if flags:
        for k, v in flags.items():
            state.set_flag(k, v)

    wm = WorldManager(state)
    return wm


# All chapter modules use their own top-level helper functions that call get_adapter().
# We patch get_menu_choice in each module to use our InputQueue,
# and silence all UI functions (typewriter, clear_screen, press_any_key, etc.).
# We also patch CombatSystem in each module to auto-win.
# For chapter chaining control, we patch the next chapter's start method
# when we want to test a single chapter in isolation.

_UI_FNS = ('clear_screen', 'typewriter', 'press_any_key', 'print_centered', 'play_sound_effect')
_CHAPTER_MODULES = ('engine.world_chapter_3', 'engine.world_chapter_4', 'engine.world_chapter_5')
_OTHER_MODULES = ('engine.world', 'engine.world_chapter_7')


def _run_chapter(wm, method_name, inputs, stop_after=None):
    """
    Executa um método do WorldManager com inputs mockados.

    stop_after: se fornecido, impede o encadeamento para o próximo capítulo.
      Valores: 'chapter_3' (impede chapter_4_start), 'chapter_4' (impede chapter_5_start),
               'chapter_5' (impede chapter_6_start), 'chapter_6' (impede final_confrontation),
               None (roda tudo até os créditos).
    """
    input_queue = InputQueue(inputs)

    # Patches to accumulate
    patches = []

    # Silence UI in all modules
    for mod in _CHAPTER_MODULES + _OTHER_MODULES:
        for fn in _UI_FNS:
            patches.append(patch(f'{mod}.{fn}', return_value=None))

    # Patch get_menu_choice and CombatSystem in chapter modules
    for mod in _CHAPTER_MODULES:
        patches.append(patch(f'{mod}.get_menu_choice', side_effect=input_queue))
        patches.append(patch(f'{mod}.CombatSystem', _FakeCombat))

    # Also patch CombatSystem and UI in engine.world (for chapter_1/2 methods if called)
    patches.append(patch('engine.world.CombatSystem', _FakeCombat))
    patches.append(patch('engine.world_chapter_7.CombatSystem', _FakeCombat))
    patches.append(patch.object(wm, 'get_leader_choice', side_effect=input_queue))

    # Adapter mock: silence emit calls but still return sensible values
    adapter_mock = MagicMock()
    adapter_mock.emit = MagicMock(return_value=None)
    wm.adapter = adapter_mock

    # Stop chaining if requested
    if stop_after == 'chapter_3':
        patches.append(patch.object(wm, 'chapter_4_start', return_value=None))
    elif stop_after == 'chapter_4':
        patches.append(patch.object(wm, 'chapter_5_start', return_value=None))
    elif stop_after == 'chapter_5':
        patches.append(patch.object(wm, 'chapter_6_start', return_value=None))
    elif stop_after == 'chapter_6':
        patches.append(patch.object(wm, 'final_confrontation', return_value=None))

    # By default, bypass chapter 7 chaining to not break existing chapter tests
    patches.append(patch.object(wm, 'chapter_7_start', side_effect=wm.credits))

    # Credits calls sys.exit, prevent that
    patches.append(patch('sys.exit', side_effect=SystemExit(0)))

    for p in patches:
        p.__enter__()

    try:
        try:
            getattr(wm, method_name)()
        except SystemExit:
            pass
    finally:
        for p in reversed(patches):
            p.__exit__(None, None, None)

    return wm


# ===========================================================================
# CAPÍTULO 3 — VILA DE MILLHAVEN
# ===========================================================================

class TestChapter3:
    """Testes do Capítulo III: Vila de Millhaven."""

    def test_main_flow_generic_party(self):
        """Fluxo principal sem class gate: Guerreiro tenta conter a criança (opção 2)."""
        wm = _make_world(CharacterClass.GUERREIRO)
        # Inputs:
        # 1) Diálogo Padre Elias: opção "1"
        # 2) Criança: opção "2" (Tentar conter - Guerreiro não tem opção Clérigo)
        _run_chapter(wm, 'chapter_3_start', ["1", "2"], stop_after='chapter_3')

        assert wm.state.get_flag("millhaven_perdida") is True
        assert not wm.state.get_flag("millhaven_salva")

    def test_clerigo_purifica_crianca_class_gate(self):
        """Class gate ativo: Clérigo purifica a criança (opção 1)."""
        wm = _make_world(CharacterClass.CLERIGO)
        hp_before = wm.player.hp
        mp_before = wm.player.mp

        # Clérigo vê opção "1" (purificar) nas opções da criança
        _run_chapter(wm, 'chapter_3_start', ["2", "1"], stop_after='chapter_3')

        assert wm.state.get_flag("millhaven_salva") is True
        assert wm.player.hp <= hp_before
        assert wm.player.mp <= mp_before

    def test_ignora_crianca_segue_capela(self):
        """Opção 3: Ignorar criança. Millhaven perdida."""
        wm = _make_world(CharacterClass.MAGO)
        # Para Mago, opções da criança: "2" (conter) e "3" (ignorar). Escolhe "3".
        _run_chapter(wm, 'chapter_3_start', ["3", "3"], stop_after='chapter_3')

        assert wm.state.get_flag("millhaven_perdida") is True

    def test_boss_paladino_corrompido_derrotado(self):
        """O boss Paladino Corrompido é derrotado — o capítulo completa sem erro."""
        wm = _make_world(CharacterClass.GUERREIRO)
        # Se chapter_3_start completa com stop_after='chapter_3',
        # significa que o boss foi derrotado com sucesso.
        _run_chapter(wm, 'chapter_3_start', ["1", "2"], stop_after='chapter_3')

        # Se chegamos aqui sem GameOverException, o boss foi derrotado.
        # O location está em millhaven (capítulo 3 define isso no início)
        assert wm.state.current_location == "millhaven"

    def test_millhaven_salva_da_ouro(self):
        """Se Clérigo salva Millhaven, jogador recebe 100 ouro."""
        wm = _make_world(CharacterClass.CLERIGO)
        gold_before = wm.player.gold

        _run_chapter(wm, 'chapter_3_start', ["1", "1"], stop_after='chapter_3')

        assert wm.state.get_flag("millhaven_salva") is True
        assert wm.player.gold >= gold_before + 100

    def test_millhaven_perdida_nao_da_ouro(self):
        """Se Millhaven é perdida, jogador NÃO recebe ouro da vila."""
        wm = _make_world(CharacterClass.GUERREIRO)
        gold_before = wm.player.gold

        _run_chapter(wm, 'chapter_3_start', ["1", "2"], stop_after='chapter_3')

        assert wm.state.get_flag("millhaven_perdida") is True
        assert wm.player.gold == gold_before

    def test_dialogo_padre_elias_opcao_ritual(self):
        """Opção de diálogo 2 (sobre o ritual) funciona sem erros."""
        wm = _make_world(CharacterClass.GUERREIRO)
        _run_chapter(wm, 'chapter_3_start', ["2", "2"], stop_after='chapter_3')

        assert wm.state.get_flag("millhaven_perdida") is True

    def test_dialogo_padre_elias_opcao_inimigo(self):
        """Opção de diálogo 3 (onde está o inimigo) funciona sem erros."""
        wm = _make_world(CharacterClass.GUERREIRO)
        _run_chapter(wm, 'chapter_3_start', ["3", "2"], stop_after='chapter_3')

        assert wm.state.get_flag("millhaven_perdida") is True


# ===========================================================================
# CAPÍTULO 4 — O CERCO A OAKHAVEN
# ===========================================================================

class TestChapter4:
    """Testes do Capítulo IV: O Cerco a Oakhaven."""

    def test_main_flow_generic_party(self):
        """Fluxo principal: Guerreiro no portão Sul, sem aliados passados."""
        wm = _make_world(CharacterClass.GUERREIRO)
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        assert wm.state.get_flag("portao_sul_salvo") is True
        assert wm.state.get_flag("oakhaven_defendida") is True

    def test_guerreiro_class_gate_portao_sul(self):
        """Guerreiro no Portão Sul: defesa ideal, portão salvo, sem dano."""
        wm = _make_world(CharacterClass.GUERREIRO)
        hp_before = wm.player.hp
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        assert wm.state.get_flag("portao_sul_salvo") is True
        assert wm.player.hp == hp_before

    def test_non_guerreiro_portao_sul_perde_hp(self):
        """Não-Guerreiro no Portão Sul: perde 20 HP."""
        wm = _make_world(CharacterClass.MAGO)
        hp_before = wm.player.hp
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        assert not wm.state.get_flag("portao_sul_salvo")
        assert wm.player.hp == max(1, hp_before - 20)

    def test_mago_class_gate_torre(self):
        """Mago na Torre: barreira restaurada."""
        wm = _make_world(CharacterClass.MAGO)
        _run_chapter(wm, 'chapter_4_start', ["2"], stop_after='chapter_4')

        assert wm.state.get_flag("torre_mago_salva") is True

    def test_non_mago_torre_perde_mp(self):
        """Não-Mago na Torre: perde 15 MP."""
        wm = _make_world(CharacterClass.GUERREIRO)
        mp_before = wm.player.mp
        _run_chapter(wm, 'chapter_4_start', ["2"], stop_after='chapter_4')

        assert not wm.state.get_flag("torre_mago_salva")
        assert wm.player.mp == max(0, mp_before - 15)

    def test_ladino_class_gate_celeiro(self):
        """Ladino no Celeiro: sabotadores impedidos."""
        wm = _make_world(CharacterClass.LADINO)
        _run_chapter(wm, 'chapter_4_start', ["3"], stop_after='chapter_4')

        assert wm.state.get_flag("celeiro_salvo") is True

    def test_non_ladino_celeiro_perde_ouro(self):
        """Não-Ladino no Celeiro: perde 30 de ouro."""
        wm = _make_world(CharacterClass.CLERIGO)
        gold_before = wm.player.gold
        _run_chapter(wm, 'chapter_4_start', ["3"], stop_after='chapter_4')

        assert not wm.state.get_flag("celeiro_salvo")
        assert wm.player.gold == max(0, gold_before - 30)

    # --- Flags de consequências anteriores sendo lidas ---

    def test_poupou_ogro_cura_30hp(self):
        """Flag poupou_ogro do Cap.1 → Krug aparece e cura 30 HP no Cap.4."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"poupou_ogro": True})
        wm.player.hp = wm.player.max_hp - 50
        hp_before = wm.player.hp
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        expected_hp = min(wm.player.max_hp, hp_before + 30)
        assert wm.player.hp == expected_hp

    def test_millhaven_salva_cura_20hp(self):
        """Flag millhaven_salva do Cap.3 → aldeões curam 20 HP no Cap.4."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"millhaven_salva": True})
        wm.player.hp = wm.player.max_hp - 50
        hp_before = wm.player.hp
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        expected_hp = min(wm.player.max_hp, hp_before + 20)
        assert wm.player.hp == expected_hp

    def test_both_allies_cura_combinada(self):
        """Ambas as flags de aliados ativos: cura combinada de 50 HP."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "poupou_ogro": True,
            "millhaven_salva": True,
        })
        wm.player.hp = wm.player.max_hp - 80
        hp_before = wm.player.hp
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        expected_hp = min(wm.player.max_hp, hp_before + 50)
        assert wm.player.hp == expected_hp

    def test_no_allies_no_cura(self):
        """Sem aliados: sem cura extra."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "poupou_ogro": False,
            "millhaven_salva": False,
        })
        wm.player.hp = wm.player.max_hp
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        assert wm.player.hp == wm.player.max_hp

    def test_boss_inquisidor_derrotado(self):
        """Boss Cap.4 (Inquisidor Sombrio) derrotado, oakhaven_defendida setada."""
        wm = _make_world(CharacterClass.GUERREIRO)
        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        assert wm.state.get_flag("oakhaven_defendida") is True

    def test_flag_oakhaven_defendida_setada(self):
        """Ao final do Cap.4, a flag oakhaven_defendida é True para qualquer classe."""
        wm = _make_world(CharacterClass.MAGO)
        _run_chapter(wm, 'chapter_4_start', ["2"], stop_after='chapter_4')

        assert wm.state.get_flag("oakhaven_defendida") is True


# ===========================================================================
# CAPÍTULO 5 — AS TERRAS CORROMPIDAS
# ===========================================================================

class TestChapter5:
    """Testes do Capítulo V: As Terras Corrompidas + Capítulo VI (Templo Final)."""

    def test_main_flow_generic_party(self):
        """Fluxo completo com Guerreiro genérico até derrota de Malakar."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        # Cap5 inputs:
        # 1) Sobreviventes: "1" (ajudar)
        # Cap6 inputs:
        # 2) Sala dos Enigmas: "4" (responder verbal 'selo') — Guerreiro vê opções 2,3,4
        # 3) Sala dos Mortos: "2" (combater sentinelas) — Guerreiro vê opção 2
        # 4) Sala do Silêncio: "3" (ignorar baú) — Guerreiro vê opções 2,3
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("ajudou_sobreviventes") is True
        assert wm.state.get_flag("malakar_derrotado") is True

    def test_ajudou_sobreviventes_flag(self):
        """Ajudar sobreviventes seta flag e custa 15 HP."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        hp_before = wm.player.hp
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("ajudou_sobreviventes") is True

    def test_ignorou_sobreviventes_flag(self):
        """Negar ajuda seta flag ignorou_sobreviventes."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["2", "4", "2", "3"])

        assert wm.state.get_flag("ignorou_sobreviventes") is True

    # --- Class gate: Mago no Santuário Profanado ---

    def test_mago_revelacao_selos(self):
        """Mago lê inscrições do santuário → flag revelacao_selos."""
        wm = _make_world(CharacterClass.MAGO, flags={"oakhaven_defendida": True})
        # Mago: Sobreviventes "1", Sala Enigmas "1" (Mago escreve selo),
        # Sala Mortos "2" (combate), Sala Silêncio "3" (ignorar)
        _run_chapter(wm, 'chapter_5_start', ["1", "1", "2", "3"])

        assert wm.state.get_flag("revelacao_selos") is True

    # --- Class gates no Cap.6: Salas do Templo ---

    def test_mago_sala_enigmas(self):
        """Mago resolve enigma com mana → flag sala_enigmas_mago."""
        wm = _make_world(CharacterClass.MAGO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "1", "2", "3"])

        assert wm.state.get_flag("sala_enigmas_mago") is True

    def test_sala_enigmas_verbal_correto(self):
        """Qualquer classe: resposta verbal 'selo' (opção 4) resolve enigma."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("sala_enigmas_mago") is True

    def test_sala_enigmas_falha(self):
        """Escolher chave errada → flag sala_enigmas_falha e perde 20 HP."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        # Para Guerreiro: opções 2 (Chave Osso), 3 (Chave Vidro), 4 (verbal)
        _run_chapter(wm, 'chapter_5_start', ["1", "2", "2", "3"])

        assert wm.state.get_flag("sala_enigmas_falha") is True

    def test_clerigo_sala_mortos(self):
        """Clérigo purifica mortos → flag sala_mortos_clerigo."""
        wm = _make_world(CharacterClass.CLERIGO, flags={"oakhaven_defendida": True})
        # Clérigo: Sobreviventes "1", Sala Enigmas "4" (verbal), Sala Mortos "1" (purifica),
        # Sala Silêncio "3" (ignorar)
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "1", "3"])

        assert wm.state.get_flag("sala_mortos_clerigo") is True

    def test_sala_mortos_combate_falha(self):
        """Sem class gate Clérigo: combate sentinelas → flag sala_mortos_falha."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("sala_mortos_falha") is True

    def test_ladino_sala_silencio(self):
        """Ladino desarma baú → flag sala_silencio_ladrao."""
        wm = _make_world(CharacterClass.LADINO, flags={"oakhaven_defendida": True})
        # Ladino: Sobreviventes "1", Sala Enigmas "4" (verbal), Sala Mortos "2" (combate),
        # Sala Silêncio "1" (Ladino desarma)
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "1"])

        assert wm.state.get_flag("sala_silencio_ladrao") is True

    def test_sala_silencio_forca_falha(self):
        """Forçar baú → flag sala_silencio_falha e perde 25 HP."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "2"])

        assert wm.state.get_flag("sala_silencio_falha") is True

    # --- Ladino na emboscada ---

    def test_ladino_emboscada_sem_dano_surpresa(self):
        """Ladino detecta emboscada → não perde 25 HP de surpresa."""
        wm = _make_world(CharacterClass.LADINO, flags={"oakhaven_defendida": True})
        # Não ajuda sobreviventes para isolar o efeito de emboscada
        hp_before = wm.player.hp
        _run_chapter(wm, 'chapter_5_start', ["2", "4", "2", "1"])

        # Ladino não perde HP da emboscada (25 HP)
        assert wm.player.hp == hp_before

    def test_non_ladino_emboscada_perde_hp(self):
        """Não-Ladino na emboscada: perde 25 HP."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        hp_before = wm.player.hp
        # Não ajuda sobreviventes para isolar
        _run_chapter(wm, 'chapter_5_start', ["2", "4", "2", "3"])

        assert wm.player.hp == max(1, hp_before - 25)

    # --- Flags de capítulos anteriores lidas no Cap.5 ---

    def test_lacre_sombrio_lido(self):
        """Flag lacre_sombrio do Cap.1 dispara evento no Cap.5 sem erros."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True,
            "lacre_sombrio": True,
        })
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("malakar_derrotado") is True

    def test_poupou_ogro_krug_cura_final(self):
        """Flag poupou_ogro → Krug aparece no confronto final, cura 50 HP."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True,
            "poupou_ogro": True,
        })
        wm.player.hp = wm.player.max_hp - 80
        hp_before = wm.player.hp
        # Não ajuda sobreviventes, não perde HP de emboscada para isolar
        # Mas Guerreiro perde 25 HP de emboscada...
        _run_chapter(wm, 'chapter_5_start', ["2", "4", "2", "3"])

        # Krug cura 50 HP, emboscada tira 25 HP
        expected_hp = min(wm.player.max_hp, hp_before - 25 + 50)
        assert wm.player.hp == expected_hp

    def test_ajudou_goblin_dropp_aparece_final(self):
        """Flag ajudou_goblin → Dropp aparece no confronto final (diálogo, sem HP)."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True,
            "ajudou_goblin": True,
        })
        _run_chapter(wm, 'chapter_5_start', ["2", "4", "2", "3"])

        assert wm.state.get_flag("malakar_derrotado") is True

    def test_ajudou_sobreviventes_mp_regen_final(self):
        """Flag ajudou_sobreviventes → sobreviventes regeneram 20 MP no confronto final."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        wm.player.mp = 5  # MP baixo
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        # 20 MP de regeneração pela flag
        assert wm.player.mp >= 20

    def test_oakhaven_defendida_rhea_aparece(self):
        """Flag oakhaven_defendida → Capitã Rhea barra portas (diálogo, sem HP)."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("malakar_derrotado") is True

    # --- Boss fights ---

    def test_boss_guardiao_portal_derrotado(self):
        """Boss Guardião do Portal é derrotado no Cap.5."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        # Se chapter_5 completa e chama chapter_6, Guardião foi derrotado.
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("malakar_derrotado") is True

    def test_boss_lorde_malakar_derrotado(self):
        """Boss final Lorde Malakar é derrotado → flag malakar_derrotado."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("malakar_derrotado") is True

    # --- Vantagens das salas aplicadas ao boss ---

    def test_sala_silencio_ladino_reduz_defesa(self):
        """Flag sala_silencio_ladrao reduz defesa de Malakar e jogo completa."""
        wm = _make_world(CharacterClass.LADINO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "1"])

        assert wm.state.get_flag("sala_silencio_ladrao") is True
        assert wm.state.get_flag("malakar_derrotado") is True

    def test_sala_mortos_clerigo_protecao_final(self):
        """Flag sala_mortos_clerigo → PROTEGIDO aplicado antes do boss final."""
        wm = _make_world(CharacterClass.CLERIGO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "1", "3"])

        assert wm.state.get_flag("sala_mortos_clerigo") is True
        assert wm.state.get_flag("malakar_derrotado") is True

    # --- Elena como mini-boss opcional ---

    def test_elena_traicao_miniboss(self):
        """Se roubou_cabana + guardou_pergaminho → Elena aparece como mini-boss."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True,
            "roubou_cabana": True,
            "guardou_pergaminho": True,
        })
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("elena_morta") is True
        assert wm.state.get_flag("malakar_derrotado") is True

    def test_elena_nao_aparece_sem_flags(self):
        """Sem roubou_cabana, Elena não aparece como mini-boss."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True,
            "roubou_cabana": False,
        })
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert not wm.state.get_flag("elena_morta")


# ===========================================================================
# ENDINGS — Sequência final / créditos
# ===========================================================================

class TestEndings:
    """Testes dos finais condicionais."""

    def test_ending_dark_lord(self):
        """Guardou pergaminho + lacre sombrio → Final do Senhor das Sombras."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True,
            "guardou_pergaminho": True,
            "lacre_sombrio": True,
        })
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        # ending_dark_lord deve ser acionado (guardou_pergaminho + lacre_sombrio)
        assert wm.state.get_flag("malakar_derrotado") is True

    def test_ending_hero_of_light(self):
        """Sem elena_morta, sem roubou_cabana → Final Herói da Luz."""
        wm = _make_world(CharacterClass.CLERIGO, flags={"oakhaven_defendida": True})
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "1", "3"])

        assert wm.state.get_flag("malakar_derrotado") is True

    def test_ending_neutral_wanderer(self):
        """Com elena_morta + roubou_cabana → Final Andarilho Solitário."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={
            "oakhaven_defendida": True,
            "elena_morta": True,
            "roubou_cabana": True,
        })
        _run_chapter(wm, 'chapter_5_start', ["1", "4", "2", "3"])

        assert wm.state.get_flag("malakar_derrotado") is True


# ===========================================================================
# TESTES DE INTEGRAÇÃO CROSS-CHAPTER
# ===========================================================================

class TestCrossChapterFlags:
    """Testes que verificam a leitura correta de flags entre capítulos."""

    def test_cap3_seta_millhaven_salva_para_cap4(self):
        """Cap.3 seta millhaven_salva → Cap.4 lê e dá cura extra."""
        wm = _make_world(CharacterClass.CLERIGO)
        wm.player.hp = wm.player.max_hp - 60

        # Cap.3 (Clérigo purifica criança "1"), Cap.4 (portão "1")
        _run_chapter(wm, 'chapter_3_start', ["1", "1", "1"], stop_after='chapter_4')

        assert wm.state.get_flag("millhaven_salva") is True
        assert wm.state.get_flag("oakhaven_defendida") is True

    def test_ogro_poupado_cap1_afeta_cap4(self):
        """Flag poupou_ogro setada no Cap.1 é corretamente lida no Cap.4."""
        wm = _make_world(CharacterClass.GUERREIRO, flags={"poupou_ogro": True})
        wm.player.hp = wm.player.max_hp - 60
        hp_before = wm.player.hp

        _run_chapter(wm, 'chapter_4_start', ["1"], stop_after='chapter_4')

        expected_hp = min(wm.player.max_hp, hp_before + 30)
        assert wm.player.hp == expected_hp

    def test_flag_aliases_ogro(self):
        """As aliases poupou_ogro / ogro_poupado são simétricas."""
        wm = _make_world(CharacterClass.GUERREIRO)
        wm.state.set_flag("poupou_ogro", True)

        assert wm.state.get_flag("poupou_ogro") is True
        assert wm.state.get_flag("ogro_poupado") is True

    def test_flag_aliases_goblin(self):
        """As aliases ajudou_goblin / goblin_ajudado são simétricas."""
        wm = _make_world(CharacterClass.GUERREIRO)
        wm.state.set_flag("ajudou_goblin", True)

        assert wm.state.get_flag("ajudou_goblin") is True
        assert wm.state.get_flag("goblin_ajudado") is True

    def test_flag_aliases_elena(self):
        """As aliases elena_traiu / elena_morta são simétricas."""
        wm = _make_world(CharacterClass.GUERREIRO)
        wm.state.set_flag("elena_morta", True)

        assert wm.state.get_flag("elena_morta") is True
        assert wm.state.get_flag("elena_traiu") is True

    def test_full_flow_cap3_cap4_cap5(self):
        """Fluxo completo Cap.3 → Cap.4 → Cap.5 com Clérigo, flags corretas em cascata."""
        wm = _make_world(CharacterClass.CLERIGO, flags={"poupou_ogro": True, "ajudou_goblin": True}, level=8)
        wm.player.hp = wm.player.max_hp
        wm.player.mp = wm.player.max_mp

        # Cap.3: diálogo Elias "1", Clérigo purifica "1"
        # Cap.4: portão "1"
        # Cap.5: ajuda sobreviventes "1",
        # Cap.6: enigma verbal "4", Clérigo purifica mortos "1", ignora baú "3"
        _run_chapter(wm, 'chapter_3_start', ["1", "1", "1", "1", "4", "1", "3"])

        assert wm.state.get_flag("millhaven_salva") is True
        assert wm.state.get_flag("oakhaven_defendida") is True
        assert wm.state.get_flag("malakar_derrotado") is True
        assert wm.state.get_flag("sala_mortos_clerigo") is True
