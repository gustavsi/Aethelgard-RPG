# RETOMADA DE TRABALHO — LEIA ANTES DE QUALQUER COISA

## Estado atual do projeto
- Fases 1-4 de refatoração: CONCLUÍDAS.
- 63 testes passando com sucesso via pytest.
- Multiplayer Cooperativo FSM e WebSocket: **Totalmente Implementados e Funcionais**.
  - **Fase de Combate WAITING_ALL_PLAYERS**: A FSM pausa no combate coletando comandos individuais de cada jogador (tanto o líder quanto membros da party).
  - **Fase de Combate PARTY_EXECUTE**: Processa as ações de todos os membros de forma ordenada pela agilidade de cada um (com desempate a favor do líder).
  - **Diferenciação no Frontend**: Jogadores veem seus próprios botões de escolha de ação de combate. O menu de alvos e habilidades de classe é personalizado por jogador e enviado de forma exclusiva para o seu respectivo WebSocket.
  - **HP Scaling**: O HP máximo dos inimigos escala dinamicamente baseado no tamanho da party (ex: +60% por jogador adicional).
  - **Feedback em tempo real (Pronto)**: Os jogadores veem a indicação de prontidão (`✅ Pronto` ou `⚔️ Decidindo...`) na lista de party na `CombatView` do frontend em tempo real à medida que as ações são submetidas.
- **Melhorias de Qualidade de Vida (QoL) da Campanha**:
  - **Auto-salvamento**: Chamada automática de `save_game()` implementada no início de todos os capítulos (2 ao 6).
  - **Menu de Preparação**: Criado `pre_boss_menu` que permite gerenciar inventário ou iniciar o combate antes de cada chefe importante (Paladino Corrompido, Inquisidor Sombrio, Elena, Guardião do Portal e Lorde Malakar).
  - **Theron como Mercador**: theron_shop adicionado após o diálogo com Theron no Capítulo 5 para compra de poções e antídotos.
  - **Feedback de Recursos**: Centralização da exibição de consumo de HP, MP, Gold e Itens através do helper `consume_resource` emitindo NarrativeText destacado com ⚠️ no chat.
- Arquivos importantes atualizados:
  - `engine/world.py`: Implementado `pre_boss_menu` e `consume_resource`. Adicionado auto-save ao Capítulo 2.
  - `engine/world_chapter_3.py`, `engine/world_chapter_4.py`, `engine/world_chapter_5.py`: Integrados auto-saves, menus de preparação de boss, loja do Theron e feedback de recursos narrativos.

## Bugs Conhecidos e Débitos Técnicos
*(Incluindo itens antigos consolidados)*

### 1. Vitória não é detectada após dano de status ou ataque de companheiro
- **Problema**: Após `enemy_turn()` and `companion_action()`, a FSM não checa se todos os inimigos morreram. Se veneno ou o companheiro matar o último inimigo, a rodada avança desnecessariamente abrindo menus sem alvos vivos.
- **Sugestão**: Centralizar checagem de morte nas fases internas e transicionar imediatamente para `VICTORY`.

### 2. Transformações de boss só ocorrem após ação direta do jogador
- **Problema**: `check_boss_transformations()` só roda em `PLAYER_EXECUTE`. Se bosses como Inquisidor ou Malakar morrerem devido a efeitos de status negativos (DoT) ou ataque do companheiro, a transformação falha em engatilhar.

### 3. Companheiros quebram ao causar dano
- **Problema**: `companion.py` assume que `Enemy.take_damage()` retorna uma tupla `(damage_dealt, desc)`, mas o método real retorna um dicionário contendo as chaves de resultado.

### 4. Menus vazios travam o jogo no console
- **Problema**: Chamar `get_menu_choice` com `{}` (ex: inventário sem itens consumíveis) gera um prompt intransponível.

### 5. XP direto no boss secreto não dispara level up
- **Problema**: `world.py` altera diretamente `self.player.xp += 100` sem passar por `Player.gain_xp()`, ignorando a lógica de progressão.

### 6. `Luz Sagrada` remove buffs positivos
- **Problema**: Purificação do clérigo limpa todo o dicionário de status de efeitos, removendo erroneamente efeitos benéficos como escudo e protegido.

### 7. Upgrades de equipamentos do Ferreiro não são salvos
- **Problema**: As melhorias na arma feitas por Garrett modificam atributos locais da instância, mas a serialização salva apenas o ID base do item, descartando os melhoramentos no reload do jogo.

## Próximas Prioridades
1. Corrigir bugs de runtime e lógica da FSM de combate relacionados a ações de companheiros e transformações de chefes (Bugs 1, 2 e 3).
2. Completar geração e atualização dos recursos visuais de sprites e backgrounds para as novas locações dos Capítulos 3 a 6.

## Regras permanentes
- Zero `print()` na engine.
- Zero `Colors.` na engine (uso exclusivo em adapters/frontend).
- Toda interação deve propagar via `emit(DTO)`.
- Rodar pytest (`python -m pytest tests/ -v`) após qualquer modificação.

## Regra Permanente de Testes
Nenhuma feature é considerada concluída sem um teste automatizado que a cubra. Ao implementar algo novo, o teste correspondente é parte da entrega — não uma etapa separada, não algo para "fazer depois". Se a feature envolve multiplayer (ações de múltiplos jogadores), o teste deve simular pelo menos 2 clientes reais via `TestClient`/WebSocket, não apenas chamar métodos Python diretamente — vários bugs neste projeto só apareceram nesse nível (payload, roteamento por client_id, ordem de mensagens), não no nível de lógica pura.
