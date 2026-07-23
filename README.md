# ⚔️ Aethelgard RPG — Crônicas de Aventura

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![React Version](https://img.shields.io/badge/react-19-cyan.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)

**Aethelgard RPG** é um jogo de RPG baseado em turnos ambientado no misterioso e perigoso reino de Aethelgard. O jogo oferece duas experiências completamente integradas: uma versão offline clássica jogada diretamente no **Terminal (Console)** e uma versão **Web Edition (Multiplayer)** rica em áudio, música ambiente, efeitos visuais e sincronização em tempo real para até 4 jogadores.

---

## ✨ Funcionalidades Principais

*   **🎮 Duas Formas de Jogar**:
    *   **Edição Web**: Interface gráfica moderna com suporte a multiplayer cooperativo (até 4 jogadores), sincronização em tempo real via WebSockets, animações de combate, áudio dinâmico e efeitos de clima.
    *   **Edição Console**: Aventura clássica de texto no terminal com suporte a cores ANSI e interações rápidas.
*   **⚔️ 4 Classes Jogáveis**:
    *   **Guerreiro**: Especialista em combate físico. Alta vitalidade, escudo protetor e dano físico robusto.
    *   **Mago**: Mestre arcano. Alta mana, feitiços de dano massivo (Bola de Fogo, Trovão) e escudos mágicos.
    *   **Ladino**: Silencioso e ágil. Alta taxa de acertos críticos, esquiva elevada e ataques furtivos ou envenenados.
    *   **Clérigo**: Servo divino. Habilidades curativas e purificadoras poderosas combinadas com punição mágica.
*   **🌳 Árvores de Talentos**: Escolhas de especialização por classe com talentos passivos e ativos que modificam estatísticas e habilidades de combate.
*   **📜 Expansão da História (Ato I & Ato II)**:
    *   **Ato I (Capítulos 1 a 6)**: Das florestas de Oakhaven às ruínas do Inquisidor.
    *   **Ato II (Capítulos 7 a 9)**: Porto de Vaelmoor, Minas de Kragmoor e o confronto final no Gélido Silêncio.
*   **📜 Sistema Narrativo, Votações & Companheiros**: Escolhas morais que impactam a história, votações em equipe nas decisões cruciais da party e companheiros recrutáveis (como Elena, Capitã Ysolde, Ulfgar e o Ogro Drogg) com habilidades ativas em combate.
*   **🏆 Modo Arena & Acampamentos**: Enfrente ondas de inimigos na Arena de Treinamento e descanse em acampamentos para recuperar HP/MP antes dos combates de chefe.
*   **🌪️ Climas & Hazards de Arena**: Condições climáticas dinâmicas (Nevoeiro, Chuva, Ventania) e perigos de terreno que afetam a precisão e o dano em combate.
*   **🛡️ Progressão & Equipamento**: Compre armas e armaduras no ferreiro, gerencie o estoque compartilhado da party e use poções/antídotos em aliados.
*   **💾 Save, Load & Reconexão**: Salve o progresso em qualquer ponto, retome a partida e reconecte em tempo real mesmo durante o combate sem perder o estado da party.
*   **🛡️ Segurança Sanitizada**: Sistema de persistência com sanitização rigorosa contra Path Traversal em IDs de salvamento (`re.sub`) e validação de nomes de arquivos.

---

## 🚀 Como Instalar e Jogar

### Pré-requisitos
*   **Python 3.10 ou superior**
*   **Node.js (v18 ou superior)** e **npm** (necessário para compilar o painel web)

### 💻 Passo 1: Inicialização Rápida (Servidor & Web)
O script de inicialização cria o ambiente virtual, instala as dependências, compila o frontend e inicia o servidor FastAPI automaticamente:

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

*   **[`engine/`](file:///home/chewbaccaun/Downloads/PIka/engine/)**: Núcleo da lógica do RPG contendo o sistema de combate FSM baseado em turnos, gerenciador de quests, itens, habilidades, árvores de talentos, clima e IA dos inimigos.
*   **[`frontend/`](file:///home/chewbaccaun/Downloads/PIka/frontend/)**: Interface web moderna construída com React 19, TypeScript e Vanilla CSS. Contém o `AudioManager` (Web Audio API) e o gerenciador de efeitos visuais.
*   **[`server.py`](file:///home/chewbaccaun/Downloads/PIka/server.py)**: Servidor FastAPI responsável por gerenciar as salas multiplayer, rotear as escolhas dos jogadores, migrar UUIDs em reconexão e coordenar os WebSockets.
*   **[`tests/`](file:///home/chewbaccaun/Downloads/PIka/tests/)**: Suite abrangente com mais de 210 testes automatizados cobrindo fluxos de combate, transformações de chefes, mortes/ressurreições, desacoplamento de rede e resiliência de salas.

---

## 📝 Licença
Este projeto é de código aberto e está sob a licença [MIT](https://opensource.org/licenses/MIT). Sinta-se livre para clonar, sugerir melhorias e criar novos capítulos para o universo de Aethelgard!
