from engine.talents import TALENTS_LIBRARY

def get_forge_menu(player, current_location, client_id, leader_id) -> dict:
    loc = current_location or "oakhaven"
    if loc == "vaelmoor":
        options = {
            "1": "Comprar Espada de Aço de Vaelmoor (60g) (+18 ATK)",
            "2": "Comprar Armadura do Corsário (90g) (+15 DEF)",
            "exit": "Voltar para o Porto"
        }
        prompt = f"⚓ Estaleiro de Vaelmoor - Seu Ouro: {player.gold}g"
    elif loc == "kragmoor":
        options = {
            "1": "Comprar Martelo de Guerra de Kragmoor (120g) (+25 ATK)",
            "2": "Comprar Armadura de Placas de Kragmoor (150g) (+22 DEF)",
            "exit": "Voltar para as Minas"
        }
        prompt = f"⚒️ Forja Rúnica de Brokk - Seu Ouro: {player.gold}g"
    else:
        options = {
            "1": "Comprar Espada de Soldado (30g) (+10 ATK)",
            "2": "Comprar Cota de Malha (50g) (+8 DEF)",
            "exit": "Voltar para a Vila"
        }
        prompt = f"⚒️ Forja de Garrett - Seu Ouro: {player.gold}g"
        
    return {
        "type": "WAITING_INPUT",
        "prompt": prompt,
        "options": options,
        "my_client_id": client_id,
        "leader_client_id": leader_id
    }

def get_talents_menu(player, client_id, leader_id) -> tuple:
    opts = {}
    idx_to_talent = {}
    count = 1
    for tid, tal in TALENTS_LIBRARY.items():
        if tal["class"] == player.char_class:
            status = "🔓 Desbloqueado" if tid in player.talents_unlocked else "🔒 Bloqueado"
            opts[str(count)] = f"{tal['name']} ({tal['desc']}) [{status}]"
            idx_to_talent[str(count)] = tid
            count += 1
    opts["exit"] = "Fechar Árvore de Talentos"
    
    payload = {
        "type": "WAITING_INPUT",
        "prompt": f"🌳 Árvore de Talentos de {player.name} (Pontos Disponíveis: {player.talent_points}) - Escolha um talento para desbloquear:",
        "options": opts,
        "my_client_id": client_id,
        "leader_client_id": leader_id
    }
    return payload, idx_to_talent

def get_tavern_menu(player, current_location, client_id, leader_id, elena_confronted: bool, elena_recrutada: bool) -> dict:
    options = {}
    loc = current_location or "oakhaven"
    
    if loc == "oakhaven":
        if not elena_recrutada and not elena_confronted:
            options["1"] = "Falar com Elena (Arqueira)"
        options.update({
            "2": "Comprar Poção de Vida Menor (5g) - Cura 25 HP",
            "3": "Comprar Poção de Mana Menor (5g) - Restaura 15 MP",
            "4": "Comprar Poção de Vida (15g) - Cura 60 HP",
            "exit": "Voltar para a Vila"
        })
        prompt = f"🍺 Taverna do Javali Saltitante - Seu Ouro: {player.gold}g"
    elif loc == "vaelmoor":
        options.update({
            "2": "Comprar Poção de Vida (15g) - Cura 60 HP",
            "3": "Comprar Poção de Mana (15g) - Restaura 40 MP",
            "4": "Comprar Poção de Vida Grande (35g) - Cura 150 HP",
            "exit": "Voltar para o Porto"
        })
        prompt = f"🍺 Taverna da Sereia Bêbada - Seu Ouro: {player.gold}g"
    elif loc == "kragmoor":
        options.update({
            "2": "Comprar Poção de Vida Grande (35g) - Cura 150 HP",
            "3": "Comprar Poção de Mana Grande (40g) - Restaura 80 MP",
            "exit": "Voltar para as Minas"
        })
        prompt = f"🍺 Taverna Subterrânea do Martelo de Ouro - Seu Ouro: {player.gold}g"
        
    return {
        "type": "WAITING_INPUT",
        "prompt": prompt,
        "options": options,
        "my_client_id": client_id,
        "leader_client_id": leader_id
    }

def get_elena_dialogue(step: int, client_id, leader_id) -> dict:
    if step == 1:
        prompt = "Você se aproxima de Elena. A arqueira ruiva olha friamente. 'Quem é você? O que quer?'"
        options = {
            "1": "\"Estou ajudando a vila investigando as cavernas. Poderia usar uma batedora talentosa.\"",
            "2": "\"Sou apenas um viajem em busca de riquezas.\"",
            "3": "\"Não importa. Queria apenas pagar uma bebida.\""
        }
    else:
        prompt = "Elena estreita os olhos e repara na sua bolsa. 'Você fala em ajudar... mas esse brilho dourado parece muito com a relíquia sagrada da nossa cabana de culto. Você roubou nosso patrimônio?'"
        options = {
            "1": "\"Sim, achei que estaria mais segura comigo.\" (Honestidade)",
            "2": "\"Não! Encontrei isso jogado na floresta.\" (Mentira)"
        }
    return {
        "type": "WAITING_INPUT",
        "prompt": prompt,
        "options": options,
        "my_client_id": client_id,
        "leader_client_id": leader_id
    }

def get_elder_menu(player, current_location, client_id, leader_id) -> dict:
    loc = current_location or "oakhaven"
    
    if loc == "vaelmoor":
        prompt = "Capitã Ysolde: \"O Armazém 7 é a chave. Maré Negra e Grum estão escondendo algo terrível lá. Preparem-se bem.\""
        options = {"exit": "Voltar para o Porto"}
    elif loc == "kragmoor":
        prompt = "Ferreiro Brokk: \"O Golem corrompido guarda a Forja. Se recuperarem a runa lendária, posso forjar armas incríveis para vocês!\""
        options = {"exit": "Voltar para as Minas"}
    else:
        quest = player.quest_manager.quests.get("cavernas")
        if quest and quest.is_completed:
            prompt = "Ancião Alistair: \"Obrigado por salvar Oakhaven libertando as Cavernas Sussurrantes! Você é um verdadeiro herói!\""
            options = {"exit": "Voltar para a Vila"}
        elif quest and quest.is_active:
            prompt = "Ancião Alistair: \"Como está indo a investigação das Cavernas Sussurrantes? O Inquisidor ainda ameaça a vila.\""
            options = {"exit": "Voltar para a Vila"}
        else:
            prompt = "Ancião Alistair: \"Viajante, você poderia nos ajudar a investigar as Cavernas Sussurrantes ao norte? O Inquisidor das Sombras está reunindo escravos e poder lá.\""
            options = {
                "1": "\"Eu irei investigar as cavernas!\"",
                "2": "\"O que eu ganho com isso?\"",
                "3": "\"Não posso ajudar agora.\"",
                "exit": "Voltar para a Vila"
            }
            
    return {
        "type": "WAITING_INPUT",
        "prompt": prompt,
        "options": options,
        "my_client_id": client_id,
        "leader_client_id": leader_id
    }

def get_elder_recompensa_menu(client_id, leader_id) -> dict:
    return {
        "type": "WAITING_INPUT",
        "prompt": "Ancião Alistair: \"Oakhaven não é rica, mas lhe daremos acesso ao nosso tesouro secreto e 100 moedas de ouro se nos salvar.\"",
        "options": {
            "1": "\"Tudo bem, aceito a missão.\"",
            "2": "\"Ainda assim, recuso.\""
        },
        "my_client_id": client_id,
        "leader_client_id": leader_id
    }
