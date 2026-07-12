# BÍBLIA DE AETHELGARD + EXPANSÃO ATO II
# Documento de referência para expansão de conteúdo — leia antes de implementar

---

# PARTE 1 — O QUE JÁ EXISTE (BÍBLIA DA HISTÓRIA)

## Premissa
O mundo de Aethelgard está em declínio. As chamas arcanas dos templos sagrados se apagam. Das profundezas, a escuridão sussurra. O antagonista central é **Lorde Malakar** — antigo humano chamado **Veyr Malakar, o Nome Primeiro**, que recusou a morte e queimou a própria alma para que "a máscara nunca caísse". Ele é protegido por selos que o tornam praticamente imortal.

## Prólogo — A Taverna do Início
Numa noite de tempestade, quatro estranhos se abrigam na mesma taverna na estrada real. Cada um faz um monólogo curto definindo sua classe (Guerreiro, Mago, Ladino, Clérigo). O grupo vota/decide um líder (em multiplayer, a escolha lista os jogadores reais conectados, não classes fixas). Pouco depois, são emboscados na estrada e acordam numa clareira na floresta.

## Capítulo 1 — A Floresta Sombria
Acordam feridos, sem lembrança clara da emboscada. Escolhem caminho (estrada antiga / floresta densa / esperar socorro / Bosque Sagrado — oculto, perigoso). Enfrentam um Salteador do Caminho. Encontram **A Cabana Abandonada**, guardada pelo **Ogro Drogg**, que se rende com pouca vida:
- **Poupar Drogg** → flag `ogro_poupado`. Ele reaparece ajudando no Capítulo 4 (defesa) e no Capítulo 6 (aliado no confronto final, cura HP).
- **Finalizar sem piedade** → XP/ouro imediato, perde o aliado.

Também podem encontrar o cadáver de um cultista com o **Lacre das Sombras** (amuleto). Guardar define `lacre_sombrio` (afeta Capítulo 5 e a fase 3 de Malakar); queimar evita essa linha.

Chegam à **Vila de Oakhaven**.

## Oakhaven (hub)
NPCs: **Taberneiro Barnaby** (Taverna do Javali Saltitante — Elena, arqueira, pode ser recrutada como companheira de toda a party), **Ferreiro Garrett** (Forja — compra/upgrade de equipamento), **Ancião Alistair** (missão das Cavernas — flag `cavernas` evita repetição). Sistema multiplayer: cada jogador navega a vila de forma independente (estágio próprio: forja/taverna/ancião) enquanto os outros fazem o mesmo; quando todos marcam "pronto", a party segue junto.

## Capítulo 2 — Cavernas Sussurrantes
Bifurcação de caminho. **Goblin Zix** encurralado — curá-lo com uma poção (`goblin_ajudado`) dá uma chave para baú dourado e atalho seguro no Capítulo 3. Boss: **Inquisidor Sombrio** (primeira aparição). Escolha sobre o **Pergaminho de Sangue**: guardar (linha sombria, ligada a `elena_traiu` depois) ou queimar.

## Capítulo 3 — A Vila de Millhaven
Vila amaldiçoada e silenciosa. **Padre Elias** (cego, fala em metáforas) revela o nome verdadeiro de Malakar. Uma criança corrompida na "casa do poço":
- **Class Gate Clérigo**: pode purificá-la (custa HP/MP) → `millhaven_salva`.
- Outras classes tentam conter e geralmente falham → `millhaven_perdida`.

Boss: **Paladino Corrompido** (ex-herói caído).

## Capítulo 4 — O Cerco a Oakhaven
Oakhaven sob ataque. **Capitã Rhea** divide a party em 3 frentes:
- Portão Sul (ideal: Guerreiro) — ogros de Malakar.
- Torre do Mago (ideal: Mago) — reativar barreira.
- Celeiro (ideal: Ladino) — sabotagem silenciosa.

Consequências anteriores reforçam aqui (Drogg ajuda se poupado; aldeões de Millhaven reforçam se salvos). Boss: **Inquisidor Sombrio** (2 fases). Define `oakhaven_defendida`.

## Capítulo 5 — As Terras Corrompidas
Travessia da terra devastada. Três eventos: acampamento de sobreviventes (ajudar = custa tempo/HP, ganha aliado; `ajudou_sobreviventes`), Santuário Profanado (Mago decifra runas e revela a origem da imortalidade de Malakar), emboscada de assassinos (Ladino detecta antes). Se `lacre_sombrio`: Malakar fala diretamente com a party, tentando corrompê-los. Se `elena_traiu`: ela aparece como mini-boss emocional. Encontram **Theron**, sobrevivente de uma party anterior, que revela as 3 fases de Malakar e agora funciona como mercador (Poção de Vida Média 80g, Poção de Mana 60g, Antídoto 40g). Boss: **Guardião do Portal**.

## Capítulo 6 — O Templo Final / Altar do Caos
Três salas antes de Malakar:
- Sala dos Enigmas (Class Gate Mago)
- Sala dos Mortos (Class Gate Clérigo)
- Sala do Silêncio (Class Gate Ladino, item lendário se bem-sucedido)

Antes do confronto final, todos os aliados conquistados são convocados conforme as flags (Drogg, Zix, aldeões de Millhaven, milícia de Oakhaven). Malakar tem 3 fases (armadura → feiticeiro → humano fraco, com diálogo específico por classe). Se `lacre_sombrio`, ganha poder extra na fase 3. Escolha final do Lacre Sombrio leva a 3 finais: **Herói da Luz**, **Senhor das Sombras**, **Andarilho Solitário**.

## Mapa de Flags de Consequência
| Flag | Origem | Efeito posterior |
|---|---|---|
| `ogro_poupado` | Cap 1 | Aliado Cap 4 e 6 |
| `goblin_ajudado` | Cap 2 | Atalho Cap 3, distrai Malakar no final |
| `lacre_sombrio` | Cap 1 | Malakar fala com a party no Cap 5, fase 3 mais forte |
| `elena_traiu` | Cap 2/5 (linha sombria) | Mini-boss emocional no Cap 5 |
| `millhaven_salva` / `millhaven_perdida` | Cap 3 | Reforço no cerco (Cap 4) |
| `oakhaven_defendida` | Cap 4 | Afeta diálogo final com Elena/Rhea |
| `ajudou_sobreviventes` | Cap 5 | Aliado extra no final |
| `party_lider` | Prólogo | Define quem tem decisão narrativa final |

## Sistemas técnicos já construídos (não tocar sem necessidade)
- FSM de combate cooperativo: cada jogador escolhe ação por rodada, resolvido por agilidade; HP dos inimigos escala com tamanho da party.
- DTOs semânticos (`NarrativeText`, `ChoiceRequested`, `AsciiArt`, `SoundEffect`, etc.) — engine nunca fala diretamente com UI.
- Inventário individual (equipamentos) + estoque compartilhado da party (consumíveis).
- Sistema de prontidão (`waiting_for_ready`) — só ativa em pontos narrativos específicos de vila, nunca no prólogo/tutorial.
- Auto-save em transição de capítulo; menu de preparo antes de cada boss.
- Lobby com código de 6 caracteres; SessionRegistry com reconexão.
- Sistema visual (`VisualEffectProvider`) e de áudio (`AudioManager`) extensíveis por registro — novo efeito = nova entrada no dicionário, sem tocar componentes.

---

# PARTE 2 — VISÃO DO ATO II

## O gancho
Malakar não era a ameaça final — era o que **segurava** algo pior. "Queimar a alma" não foi loucura: foi o preço de manter um selo. Com sua morte (ou corrupção, dependendo do final), **O Vazio Que Malakar Silenciava** começa a despertar.

## Epílogos por final (curtos, convergem no mesmo gancho)

**Herói da Luz**: *"Meses depois de Oakhaven ser reconstruída, os templos voltam a acender suas chamas. Mas em uma noite sem lua, um mensageiro chega maltrapilho de Vaelmoor: 'Algo mais fundo do que Malakar está se mexendo. E ele sabia. Por isso queimou a própria alma.'"*

**Senhor das Sombras**: *"O poder de Malakar corre agora nas suas veias, mas com ele veio o peso de saber a verdade: você não herdou um trono, herdou uma guarda. Algo abaixo do trono sente sua fraqueza e testa os limites do selo."*

**Andarilho Solitário**: *"Você seguiu sozinho, longe de Oakhaven, tentando esquecer. Mas os pesadelos não pararam — e um deles trouxe consigo o nome de um porto que você nunca visitou: Vaelmoor."*

## Antagonista do Ato II
**Vesper, Arauto do Vazio** — ex-acólita da ordem original de Malakar, agora serve à entidade que ele continha. Não é uma vilã de força bruta — é manipuladora, aparece em confrontos narrativos (foge em vez de morrer), e vai crescendo como rival recorrente ao longo do Ato II.

---

# PARTE 3 — MAPA DE CONTEÚDO NOVO

## Novas regiões (roadmap — só a primeira será detalhada agora)

| Capítulo | Região | Gancho | Boss |
|---|---|---|---|
| 7 (DETALHADO ABAIXO) | Porto de Vaelmoor | Contrabando de um artefato do Vazio pela facção "Maré Negra" | Contramestre Grum, o Afogado |
| 8 (esboço) | Minas de Kragmoor | Forja ancestral anã, conflito de mineração, desbloqueia crafting de equipamento lendário | Golem de Kragmoor (guardião da forja) |
| 9 (esboço) | O Gélido Silêncio | Tribos bárbaras do norte guardam parte da lore do selo original | Uivador do Vazio (fera colossal) |
| 10 (esboço) | Ruínas de Vaelthir | Dungeon late-game estilo "raid", múltiplos mini-bosses | Vesper (confronto final do Ato II) |

Cada região = arquivo próprio (`engine/world_chapter_7.py`, etc.), seguindo exatamente o padrão dos capítulos 3-5: emit via DTO, flags via `state.set_flag`/`get_flag`, class gates via `any(p.char_class == X for p in party)`.

## Sistema de Side Quests (novo, genérico e reutilizável)
Crie `engine/side_quests.py` com um padrão simples:
```python
class SideQuest:
    def __init__(self, id, name, giver_npc, flag_complete, reward_fn):
        ...
```
Qualquer vila pode ter um "quadro de recompensas" opcional. Side quests nunca bloqueiam a main quest — são puramente opcionais, com recompensa em equipamento/ouro/lore.

## Tiers de Equipamento
Expandir `items.py` com raridade: Comum → Raro → Épico → Lendário. Ferreiros regionais (Garrett em Oakhaven, um novo em Kragmoor) fazem upgrade usando materiais coletados em masmorras (sistema leve de crafting — não precisa ser complexo, só um "material_id" + quantidade).

## Novos Companheiros
Cada nova região pode ter 1 companheiro recrutável via side quest, com habilidade única em combate — seguindo o mesmo padrão de `ElenaCompanion`/`DroggCompanion`.

## Eventos de Estrada (leve, opcional)
Sistema de "encontro de viagem" entre capítulos — pequenos eventos curtos e opcionais (comboio de mercadores, clima hostil, escaramuça menor) para dar textura sem exigir muito código novo.

## Class Gates Combinados (novidade)
Agora que a party tem composição real, alguns puzzles podem exigir DUAS classes ao mesmo tempo (ex: Mago segura uma barreira enquanto o Ladino desarma uma armadilha). Use nos capítulos 8-10 para variar a mecânica dos gates simples do Ato I.

## Áudio/Visual necessários para o Ato II
- Cenários: `cenario_vaelmoor.jpg` (porto), `cenario_kragmoor.jpg` (minas), `cenario_gelido.jpg` (norte), `cenario_vaelthir.jpg` (ruínas)
- Sprites: Vesper, Contramestre Grum, Golem de Kragmoor, Uivador do Vazio
- Música: tema de porto/contrabando, tema de forja anã, tema ventania nórdica, tema de ruínas afundadas

---

# PARTE 4 — CONTEÚDO SEMENTE: CAPÍTULO 7 (DETALHADO)

## Porto de Vaelmoor
Arquivo: `engine/world_chapter_7.py`

### Chegada (narração)
*"O cheiro de sal e óleo de baleia anuncia Vaelmoor antes que vocês a vejam. É uma cidade de madeira empilhada sobre madeira, guindastes rangendo, e gaivotas gritando como se soubessem de algo que os humanos ainda não sabem. Nos becos, uma tatuagem de onda negra aparece em mais de um pulso apressado."*

### NPC principal: Capitã Ysolde
Corsária/mestra do porto, cética mas justa. Ela conta que a facção **Maré Negra** anda contrabandeando algo "que não deveria estar fora d'água" — um artefato envolto em correntes, guardado no Armazém 7.

Diálogo (trecho):
> *"Não me interessa política de deuses mortos, viajantes. Me interessa que minha cidade não afunde por causa de uma caixa que ninguém quis abrir. Ajudem-me a descobrir o que é, e eu ajudo vocês a chegar mais rápido a onde quer que estejam indo."*

### Class Gate (escolha de abordagem ao Armazém 7)
- **Ladino**: infiltra-se pelos telhados, evita o combate inteiro → `vaelmoor_infiltrado`.
- **Guerreiro**: desafia o capanga da Maré Negra para um duelo por informação → `vaelmoor_duelo_vencido`.
- **Mago**: identifica os selos rúnicos na caixa contrabandeada, revelando que é um fragmento do que Malakar continha → `vaelmoor_selo_identificado`.
- **Clérigo**: sente a corrupção nos tripulantes marcados pelo Vazio antes que ataquem → `vaelmoor_corrupcao_sentida`.

Cada gate bem-sucedido reduz a dificuldade do boss ou dá uma vantagem tática (menos inimigos, buff inicial, etc.) — sem classe ideal presente, o grupo enfrenta o caminho difícil (combate extra).

### Confronto com Vesper (narrativo, não é boss)
Vesper aparece brevemente supervisionando o carregamento, troca falas ameaçadoras e foge por um alçapão antes de qualquer combate real ser possível.
> *"Vocês mataram um homem que carregava um fardo pesado demais para vocês entenderem. Não vão gostar do que sai de baixo dele."*

Define `vesper_confrontada` (flag narrativa para recorrência no Ato II).

### Boss: Contramestre Grum, o Afogado
Antigo imediato do navio, corrompido por cracas do Vazio que o mantêm "vivo" além da morte natural. Combate com temática aquática (maré, correntes, afogamento como efeito de status).

### Recrutamento opcional
Se a party ajudar Ysolde de forma satisfatória (gate bem-sucedido + Grum derrotado), ela pode se juntar como companheira (`capitã_ysolde_aliada`) — habilidade de combate baseada em tiro de arpéu/controle de posicionamento.

---

# PARTE 5 — INSTRUÇÕES PARA O GEMINI

Antes de escrever qualquer código:

1. Leia este documento inteiro.
2. Leia `engine/world_chapter_5.py` para revisar o padrão de implementação de capítulo (DTOs, flags, class gates, boss).
3. Proponha um plano de implementação modular e faseado — **não implemente nada ainda**. O plano deve responder:
   - Como o Ato II se conecta ao final do Capítulo 6 sem reescrever os 3 finais existentes? (sugestão: um "gancho de epílogo" curto e universal, chamado logo após qualquer um dos 3 finais, antes de encerrar a sessão)
   - Estrutura de arquivo para o Capítulo 7 (`world_chapter_7.py`) seguindo o padrão existente
   - Onde ficará o sistema de side quests (`side_quests.py`) e como ele se conecta a `world.py` sem acoplamento forte
   - Como as novas flags (`vaelmoor_*`, `vesper_confrontada`, etc.) serão adicionadas ao sistema existente sem conflitar com as atuais

4. Regras permanentes que continuam valendo:
   - Zero `print()`/`Colors.` na engine — tudo via `emit(DTO)`
   - Class gates via `any(p.char_class == X for p in self.party)`
   - Testes automatizados cobrindo o novo capítulo antes de declarar concluído
   - Um capítulo/sistema por vez, com aprovação entre eles — não implemente o Ato II inteiro de uma vez

5. Não toque nos Capítulos 1-6 exceto para adicionar o gancho de epílogo delimitado no ponto exato de cada final.

Aguarde aprovação do plano antes de escrever qualquer linha de conteúdo do Capítulo 7.
