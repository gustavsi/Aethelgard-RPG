# Auditoria e Plano de Arquitetura: Aethelgard Engine (Revisão 2.0)

## 1. Auditoria da Arquitetura Atual
O projeto atual foi concebido como um script linear, onde a lógica de negócios e a renderização (UI) coexistem bloqueando o fluxo de execução através de `input()`. Essa arquitetura impossibilita o multiplayer, escalabilidade sistêmica e testes automatizados assíncronos.

## 2. A Nova Arquitetura Proposta (Orientada a ECS e Eventos)

A engine será migrada para uma arquitetura "Client-Server" profissional.

### Os 4 Pilares Arquiteturais:
1. **Mentalidade ECS (Entity Component System) Simples**:
   - Em vez de classes rígidas isoladas (`Player`, `Enemy`, `NPC`), teremos o conceito de **Entity**. 
   - Entidades recebem **Components** (ex: `Health`, `Inventory`, `Combat`, `Merchant`, `Dialogue`). Isso maximiza a reutilização de código e previne heranças gigantes.
2. **Identificadores Únicos (UUIDs)**:
   - Todo objeto no jogo possuirá um ID (`player_0001`, `sword_iron_032`, `quest_001`, `goblin_04`). Toda comunicação (ataques, trocas, movimentações) girará em torno de IDs em vez de ponteiros de memória de objetos.
3. **Eventos + Snapshot de Estado (`GET_STATE`)**:
   - A Engine recebe **Commands**, transmuta o estado e cospe **Events** (para deltas rápidos).
   - Simultaneamente, a arquitetura garante a capacidade de extrair um **Snapshot** total. Se um cliente desconecta e volta, ele requisita um `GET_STATE` e redesenha a tela instantaneamente, sem precisar re-processar mil eventos perdidos.
4. **Hierarquia Dimensional (World > Session > Player)**:
   - O Backend é agnóstico. Ele hospeda um **World**.
   - O World contém múltiplas **Sessions** (podendo ser um Mapa Aberto, uma Masmorra Privada de 4 players, ou uma Arena PvP).
   - As Sessions gerenciam as instâncias de **Players** dentro de si.

## 3. Plano de Migração (Step-by-Step)

### Etapa 0: A Blindagem (Testes de Regressão)
- **Ação**: Nenhuma linha do código principal será alterada. Antes, construiremos uma suite exaustiva de testes automatizados (`pytest`).
- **Como**: Usaremos mocks para injetar sequências de inputs virtuais simulando fluxos completos:
  - `test_criar_personagem()`
  - `test_combate_vitoria()`
  - `test_compra_venda_item()`
  - `test_subir_nivel()`
  - `test_save_load()`
- **Regra**: Cada etapa futura exige 100% de sucesso (verde) na bateria de testes.

### Etapa 1: Desacoplamento de Logs e Modelagem (Refatoração de Modelos)
- Limpar os models. Remover strings ANSI (cores) de dentro do motor numérico. Os modelos purificados passarão a expor os dados para formatação externa.

### Etapa 2: Adoção do State Machine e Remoção dos Loops Bloqueantes (O Fim do Terminal)
- Transmutar os blocos `while True` para uma **Máquina de Estados Finita (FSM)** baseada em Comandos.
- A Engine não pausa mais esperando um input. Ela registra que está no estado `WAITING_FOR_MENU` e desocupa o processador até receber a interrupção.

### Etapa 3: Construção do Event Bus e Identidade (UUIDs)
- Refatorar a criação de objetos para assinarem IDs universais.
- A Engine publicará eventos formais no Event Bus (ex: `EntityDamagedEvent`, `InventoryUpdatedEvent`).

### Etapa 4: Camada de Transporte Multi-Cliente e Snapshots
- Adaptação definitiva do `server.py` e do React.
- O React consumirá pacotes polidos (Eventos) e invocará `GET_STATE` para forçar renderizações seguras (anti-lag).

### Etapa 5: Expansão ECS e Hierarquia de Sessões
- Desmembrar heranças em Composição (Components).
- Implantar o sistema `World -> Session -> Player` para habilitar instâncias instanciadas (PvP, Lobbies e Dungeons independentes na mesma porta 8000).
