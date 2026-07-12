# Verified Architecture Review — PIKA RPG (Aethelgard)

Este documento apresenta uma revisão de arquitetura completa do projeto, avaliando detalhadamente a validade do plano de correção existente (`plano_de_correcao.txt`) e identificando novos problemas arquiteturais críticos com foco em sustentabilidade a longo prazo e compatibilidade com múltiplos jogadores.

---

## 1. Executive Summary

### Avaliação Geral
O plano de correção proposto (`plano_de_correcao.txt`) identificou corretamente a maioria dos sintomas superficiais de bugs (como a falta de atualização de localização em `world.py` e problemas de renderização visual/UX). No entanto, o plano peca ao tratar os bugs isoladamente, sem perceber que a raiz deles reside em decisões fundamentais da arquitetura da engine:
1. **Redirecionamento de console para web baseado em estado thread-local** (`console.py`).
2. **Padrão de projeto Singleton estático** (`UIAdapter._instance`) que impossibilita concorrência e suporte multiplayer.
3. **Persistência em arquivo global único** (`savegame.json`).

### Confiabilidade do Plano Existente
* **Confiabilidade**: **75%** (Identifica problemas de UI e bugs locais, mas ignora completamente os riscos concorrentes e multiplayer).

---

## 2. Architecture Overview

A engine de PIKA opera como um **sistema narrativo acoplado a um fluxo síncrono com blocking inputs**.
- O backend (`server.py`) expõe uma rota WebSocket. Cada nova conexão inicia uma thread de execução dedicada em `run_engine_thread`.
- O adaptador de entrada (`WebUIAdapter`) simula um fluxo de console bloqueando a thread através de um `queue.Queue` no método `_wait_for_input()`.
- O estado narrativo é atualizado sequencialmente via controle imperativo no arquivo `world.py`.
- O estado de combate (`CombatSystem`) executa um loop interno de fases (`CombatPhase`) e dispara atualizações do dicionário `combat_state` no `GameState`.

---

## 3. Review of Existing Plan

### BUG-01: current_location nunca atualizado
* **Status**: ✅ VERIFIED
* **Evidence**: Em versões anteriores de `world.py`, a propriedade `current_location` não era alterada. Na versão atual, foi alterada manualmente em métodos como `chapter_1_road` e `chapter_1_forest`.
* **Proposed Fix Review**: Funciona para alterar imagens de fundo, mas depende de strings mágicas distribuídas pela narrativa. 
* **Multiplayer Impact**: Para multiplayer, se a localização for global por sessão de jogo, a sincronização de jogadores em uma mesma sala exigirá um gerenciamento centralizado de zonas.

### BUG-02: test_flows.py instantiates CombatSystem with Player, not GameState
* **Status**: ✅ VERIFIED
* **Evidence**: Os testes em `tests/test_flows.py` foram ajustados para instanciar `CombatSystem(state, [enemy])`.
* **Proposed Fix Review**: Correto e alinhado com o fluxo de produção.

### BUG-03: uiContext never cleared on STATE_UPDATE without WAITING_INPUT
* **Status**: ✅ VERIFIED
* **Evidence**: Implementado em `WebSocketProvider.tsx`.
* **Proposed Fix Review**: Remove botões antigos. Contudo, limpar o contexto indiscriminadamente pode causar condições de corrida caso atualizações de estado assíncronas cheguem no meio de um fluxo de input pendente.

### BUG-04: WebSocketProvider does not reconnect after connection drop
* **Status**: ✅ VERIFIED
* **Evidence**: Implementado em `WebSocketProvider.tsx` com mecanismo de backoff exponencial.
* **Proposed Fix Review**: Tenta se reconectar ao WebSocket. Entretanto, reconectar cria um *novo* fluxo de thread no backend a partir do zero (reseta a narrativa), invalidando a reconexão útil se não houver preservação de sessão no servidor.

### BUG-05: server.py /api/game/load creates a new game instead of loading
* **Status**: ✅ VERIFIED
* **Evidence**: Ajustado em `server.py` buscando persistir a sessão via payload do tipo `load`.
* **Proposed Fix Review**: Correto para jogador único, mas busca sempre do arquivo global estático `savegame.json`.

### BUG-06: play_sound_effect does not route to web bridge
* **Status**: ✅ VERIFIED
* **Evidence**: Corrigido no método `play_sound_effect` em `console.py`.

### BUG-07: draw_box does not route to web bridge
* **Status**: ✅ VERIFIED
* **Evidence**: Implementado handler `"BOX"` no `BridgeWrapper` em `server.py`.

### BUG-08: GameState.to_dict() - combat_state.copy() is a shallow copy
* **Status**: ✅ VERIFIED
* **Evidence**: Alterado para `copy.deepcopy` em `state.py`.

### BUG-09: CombatView buttons do not wrap long text
* **Status**: ✅ VERIFIED
* **Evidence**: Adicionado `whitespace-normal text-left h-auto` em `CombatView.tsx`.

### BUG-10: console.log of debug forgotten
* **Status**: ✅ VERIFIED
* **Evidence**: Envolvido em verificação de ambiente em `NarrativeView.tsx`.

---

## 4. New Problems Discovered

### 🔴 Problem A: Concorrência Quebrada no UIAdapter Singleton
- **Evidência**: Em `engine/adapter.py`, a classe `UIAdapter` guarda o estado estático `_instance = None`. Em `server.py` (linha 80), a inicialização chama `UIAdapter.set_instance(adapter)`.
- **Impacto**: Se dois usuários jogarem ao mesmo tempo, a chamada do segundo jogador sobrescreve o adaptador estático da classe para ambos. Os inputs do jogador A passarão a ir para a sessão do jogador B, bloqueando ou enviando comandos errados.

### 🔴 Problem B: Abstração de Save Global Única
- **Evidência**: Em `save_system.py`, o caminho do save é fixado como `savegame.json`.
- **Impacto**: Não há isolamento de save. Múltiplos jogadores salvando sobrescrevem o mesmo arquivo central.

### 🟡 Problem C: Loop de Animação de Combate CLI Ativo na Web
- **Evidência**: `CombatUI.run` (usado na Web através de importação) contém loops que chamam `draw_screen()` e `time.sleep(0.5)`.
- **Impacto**: A engine gasta tempo desenhando caixas em ASCII no terminal do servidor e adormecendo a thread síncrona sem necessidade quando executada na web.

---

## 5. Architectural Weaknesses

1. **Acoplamento Monolítico da Interface**: A engine de jogo decide como as caixas de texto são estruturadas (`draw_box`, `print_centered`) em vez de simplesmente fornecer eventos semânticos com os dados estruturados.
2. **Ciclo de Vida de Conexão Acoplado à Thread**: A thread de execução do jogo morre imediatamente quando a conexão WebSocket fecha. Quedas rápidas de rede exigem reinício total da aventura.

---

## 6. Future Multiplayer Readiness

### Avaliação de Prontidão (0 a 10): 2 / 10

* **Networking Readiness**: Muito baixa. A engine assume uma única thread síncrona com entradas bloqueantes nativas.
* **State Synchronization**: Frágil. Depende de snapshots totais do estado via lock mutável (`GameState.lock`).
* **Server Authority**: Média. O servidor executa toda a lógica, mas o design atual permite que o cliente de forma assíncrona mande strings que o adaptador não valida profundamente.
* **Save/Load Compatibility**: Inexistente para múltiplos usuários.

---

## 7. Technical Debt

1. **Débito Imediato (Alta Prioridade)**:
   - Eliminação da propriedade de classe `UIAdapter._instance` global em favor de instâncias locais.
   - Parametrizar a gravação de arquivos de save por Session ID em `save_system.py`.
2. **Débito de Médio Prazo**:
   - Remoção completa de wrappers de saída de terminal (`draw_box`, `draw_two_columns`) ao jogar em modo Web.
3. **Débito de Longo Prazo**:
   - Transição da engine síncrona baseada em threads bloqueantes para uma arquitetura orientada a eventos assíncronos não-bloqueantes.

---

## 8. Recommended Order of Implementation

1. **Refatorar Injeção de Adaptador**: Remover o singleton global de `UIAdapter` e injetar instâncias localmente nos construtores do jogo.
2. **Parametrizar Save System**: Adicionar identificador de sessão nos métodos de persistência.
3. **Remover Dead-Code do CLI**: Isolar saídas de terminal em modo web para reduzir gargalos de processamento.
4. **Estabelecer Teste de Isolamento de Concorrência**: Criar testes automatizados simulando múltiplos usuários agindo simultaneamente no WebSocket.
