import random
from typing import List
from engine.enemy import Enemy
from engine.constants import AIType, Colors
from engine.combat import CombatSystem
from engine.world import typewriter, press_any_key

def generate_arena_enemies(wave: int) -> List[Enemy]:
    # Scale factor
    scale = 1.0 + (wave - 1) * 0.15
    
    # Wave archetypes
    if wave % 5 == 0:
        # Boss wave!
        boss_names = ["Malakar Arena", "Inquisidor do Coliseu", "Titã de Ferro", "Elena Sombria"]
        boss_name = random.choice(boss_names)
        ai_types = [AIType.BOSS_MALAKAR, AIType.BOSS_INQUISITOR, AIType.BOSS_GOLEM, AIType.BOSS_OGRE]
        ai_type = random.choice(ai_types)
        
        return [
            Enemy(
                name=boss_name,
                hp=int(300 * scale),
                attack=int(25 * scale),
                defense=int(12 * scale),
                xp_reward=100 * wave,
                gold_reward=50 * wave,
                ai_type=ai_type
            )
        ]
    elif wave % 3 == 0:
        # Mini-boss/Ogre wave
        return [
            Enemy(
                name="Ogro de Guerra",
                hp=int(150 * scale),
                attack=int(18 * scale),
                defense=int(8 * scale),
                xp_reward=60 * wave,
                gold_reward=30 * wave,
                ai_type=AIType.BOSS_OGRE
            )
        ]
    else:
        # Standard wave of 1 to 3 enemies
        enemies_count = min(3, random.randint(1, 2) + (wave // 4))
        pool = [
            ("Goblin Gladiador", 60, 10, 3, AIType.AGGRESSIVE),
            ("Lobo das Sombras", 50, 12, 2, AIType.AGGRESSIVE),
            ("Gárgula de Pedra", 80, 8, 6, AIType.DEFENSIVE),
            ("Mago Sombrio", 55, 14, 1, AIType.AGGRESSIVE)
        ]
        
        res = []
        for i in range(enemies_count):
            base_name, base_hp, base_atk, base_def, ai = random.choice(pool)
            name = f"{base_name} {chr(65+i)}" if enemies_count > 1 else base_name
            res.append(
                Enemy(
                    name=name,
                    hp=int(base_hp * scale),
                    attack=int(base_atk * scale),
                    defense=int(base_def * scale),
                    xp_reward=20 * wave,
                    gold_reward=10 * wave,
                    ai_type=ai
                )
            )
        return res

def apply_hp_blessing(party):
    for p in party:
        p.max_hp += 20
        p.hp += 20

def apply_mp_blessing(party):
    for p in party:
        p.max_mp += 15
        p.mp += 15

def apply_forca_blessing(party):
    for p in party:
        p.forca += 4

def apply_inteligencia_blessing(party):
    for p in party:
        p.inteligencia += 4

def apply_agilidade_blessing(party):
    for p in party:
        p.agilidade += 4

def apply_ouro_blessing(party):
    for p in party:
        p.gold += 100

def apply_talentos_blessing(party):
    for p in party:
        p.talent_points += 1

def run_arena_loop(world, adapter):
    typewriter(f"\n🏰 {Colors.BOLD}BEM-VINDO À ARENA DE AETHELGARD!{Colors.RESET}", 0.02)
    typewriter("Sua party enfrentará ondas infinitas de monstros no Coliseu do Vazio.", 0.02)
    typewriter("Entre cada onda, você receberá bênçãos e bônus passivos para ajudar na sobrevivência.", 0.02)
    typewriter("Boa sorte, heróis. Vocês vão precisar.\n", 0.02)
    press_any_key()
    
    wave = 0
    while True:
        wave += 1
        world.state.set_flag("arena_wave", wave)
        
        # Auto-update location to change weather/time of day
        world.state.current_location = "arena"
        
        typewriter(f"\n⚡ {Colors.BOLD}ONDA {wave}{Colors.RESET} ⚡", 0.02)
        typewriter("Aparecendo inimigos no portão do Coliseu...", 0.02)
        
        # Heal 30% HP and restore 100% MP
        for p in world.party:
            heal_amt = int(p.max_hp * 0.3)
            p.hp = min(p.max_hp, p.hp + heal_amt)
            p.mp = p.max_mp
            typewriter(f"💖 {p.name} recuperou {heal_amt} HP e toda a Mana.", 0.02)
            
        enemies = generate_arena_enemies(wave)
        
        combat = CombatSystem(world.state, enemies, can_flee=False, adapter=adapter)
        world.active_combat = combat
        
        # Force state update to clients
        adapter.on_state_change(world.state)
        
        combat_res = combat.run()
        
        # Check defeat
        if not combat_res:
            typewriter(f"\n💀 {Colors.BOLD}DERROTA!{Colors.RESET} A party foi eliminada na Onda {wave}.", 0.02)
            break
            
        # Give rewards
        xp_gain = 50 * wave
        gold_gain = 25 * wave
        typewriter(f"\n🎉 {Colors.BOLD}ONDA {wave} CONCLUÍDA!{Colors.RESET}", 0.02)
        for p in world.party:
            p.gold += gold_gain
            typewriter(f"💰 {p.name} ganhou {gold_gain} de ouro.", 0.02)
            logs = p.gain_xp(xp_gain)
            for log in logs:
                typewriter(log, 0.02)
                
        # Draft of Buffs
        draft_options = [
            ("hp", "Bênção da Vitalidade (+20 Max HP para toda a Party)", apply_hp_blessing),
            ("mp", "Bênção da Mente (+15 Max MP para toda a Party)", apply_mp_blessing),
            ("forca", "Bênção do Arsenal (+4 Força para toda a Party)", apply_forca_blessing),
            ("inteligencia", "Bênção do Conhecimento (+4 Inteligência para toda a Party)", apply_inteligencia_blessing),
            ("agilidade", "Bênção do Vento (+4 Agilidade para toda a Party)", apply_agilidade_blessing),
            ("ouro", "Bolsa de Tesouro (+100 Ouro para cada membro)", apply_ouro_blessing),
            ("talentos", "Estrela de Talento (+1 Ponto de Talento para cada membro)", apply_talentos_blessing),
        ]
        
        # Select 3 random unique options
        selected_draft = random.sample(draft_options, 3)
        opts = {str(i+1): text for i, (_, text, _) in enumerate(selected_draft)}
        
        # Ask leader
        choice = world.get_leader_choice(opts, prompt=f"🏆 VITÓRIA! Escolha seu Buff de Recompensa para a Onda {wave}:")
        
        chosen_buff = selected_draft[int(choice) - 1]
        # Apply effect
        chosen_buff[2](world.party)
        typewriter(f"\n✨ Aplicado: {chosen_buff[1]}\n", 0.02)
        press_any_key()
        
    # Game Over
    adapter.ws_callback({"type": "GAME_OVER", "prompt": f"Você sucumbiu ao Coliseu na Onda {wave}."})
