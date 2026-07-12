# ⚔️ Aethelgard RPG — Crônicas de Aventura

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![React Version](https://img.shields.io/badge/react-19-cyan.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)

**Aethelgard RPG** é um jogo de RPG baseado em turnos ambientado no misterioso e perigoso reino de Aethelgard. O jogo oferece duas experiências completamente integradas: uma versão offline clássica jogada diretamente no **Terminal (Console)** e uma versão **Web Edition (Multiplayer)** rica em áudio, música ambiente e efeitos visuais em tempo real para até 3 jogadores.

---

## ✨ Funcionalidades Principais

*   **🎮 Duas Formas de Jogar**:
    *   **Edição Web**: Interface gráfica moderna com suporte a multiplayer cooperativo, sincronização em tempo real via WebSockets, animações de projéteis e cura, além de trilhas sonoras dedicadas para cada ambiente.
    *   **Edição Console**: Aventura clássica de texto no terminal com suporte a cores ANSI e interações rápidas.
*   **⚔️ 5 Classes Jogáveis**:
    *   **Guerreiro**: Especialista em combate físico. Alta vitalidade, escudo protetor e dano físico robusto.
    *   **Mago**: Mestre arcano. Alta mana, feitiços de dano massivo (Bola de Fogo, Trovão) e escudos mágicos.
    *   **Ladino**: Silencioso e ágil. Alta taxa de acertos críticos, esquiva elevada e ataques furtivos ou envenenados.
    *   **Clérigo**: Servo divino. Habilidades curativas e purificadoras poderosas combinadas com punição mágica.
    *   **Arqueiro**: Caçador preciso. Ataques perfurantes de longa distância e tiros rápidos.
*   **📜 Sistema Narrativo & Quests**: Escolhas que impactam a história (como poupar ou enfrentar o Ogro), missões secundárias ativas e companions recrutáveis (como a capitã Ysolde ou Elena) que ajudam você no combate.
*   **🛡️ Progressão & Equipamento**: Compre armas e armaduras no ferreiro, compre poções e antídotos nos mercadores e aprimore seus atributos subindo de nível.
*   **💾 Save & Load**: Salve seu progresso a qualquer momento no capítulo e retome sua jornada posteriormente de forma automática.
*   **🛡️ Segurança de Ponta**: Sistema de persistência com sanitização robusta contra Path Traversal em saves e integridade de sessões.

---

## 🚀 Como Instalar e Jogar

### Pré-requisitos
*   **Python 3.10 ou superior**
*   **Node.js (v18 ou superior)** e **npm** (necessário para compilar o painel web)

### 💻 Passo 1: Inicialização Rápida (Servidor & Web)
O script de inicialização compila o frontend e inicia o servidor FastAPI automaticamente:

```bash
# Deixe o script start.sh executável (caso esteja no Linux/macOS)
chmod +x start.sh

# Execute o inicializador
./start.sh
```

Acesse o jogo no navegador em: **[http://localhost:4230](http://localhost:4230)**.

### 📟 Passo 2: Jogar pelo Terminal (Offline/Singleplayer)
Se preferir a experiência clássica puramente via texto no terminal, execute:

```bash
python3 game.py
```

---

## 🛠️ Arquitetura do Projeto

*   **[`engine/`](file:///home/chewbaccaun/Downloads/PIka/engine/)**: Núcleo da lógica do RPG contendo o sistema de combate baseado em turnos, gerenciador de quests, itens, habilidades e IA dos inimigos.
*   **[`frontend/`](file:///home/chewbaccaun/Downloads/PIka/frontend/)**: Interface web moderna construída com React 19, TypeScript e Tailwind CSS. Contém o `AudioManager` (Web Audio API) e o gerenciador de efeitos visuais.
*   **[`server.py`](file:///home/chewbaccaun/Downloads/PIka/server.py)**: Servidor FastAPI responsável por gerenciar as salas multiplayer, rotear as escolhas dos jogadores e coordenar as conexões WebSocket.
*   **[`tests/`](file:///home/chewbaccaun/Downloads/PIka/tests/)**: Suite abrangente com mais de 130 testes automatizados cobrindo fluxos de combate, transformações de chefes, mortes/ressurreições e integridade de rede.

---

## 📝 Licença
Este projeto é de código aberto e está sob a licença [MIT](https://opensource.org/licenses/MIT). Sinta-se livre para clonar, sugerir melhorias e criar novos capítulos para o universo de Aethelgard!
