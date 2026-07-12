import React, { useState, useEffect } from 'react';
import { WebSocketProvider, useGame } from './contexts/WebSocketProvider';
import { GameContainer } from './components/GameContainer';
import { LobbyView } from './components/LobbyView';
import { VisualEffectProvider } from './contexts/VisualEffectProvider';

const LobbyOrGameWrapper: React.FC<{ lobbyCode: string, isCreator: boolean }> = ({ lobbyCode, isCreator }) => {
  const { gameStarted } = useGame();
  if (gameStarted) {
    return <GameContainer />;
  }
  return <LobbyView lobbyCode={lobbyCode} isCreator={isCreator} />;
};

function App() {
  const [screen, setScreen] = useState<'menu' | 'character_selection' | 'lobby' | 'game_direct'>('menu');
  const [joinMode, setJoinMode] = useState<'create' | 'join'>('create');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lobbyCode, setLobbyCode] = useState<string>('');
  const [lobbyInput, setLobbyInput] = useState<string>('');
  
  // Character state
  const [playerName, setPlayerName] = useState<string>('');
  const [playerClass, setPlayerClass] = useState<string>('GUERREIRO');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedGame, setSavedGame] = useState<{
    session_id: string;
    player_name: string;
    chapter: number;
    location: string;
  } | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('pika_save');
      if (stored) {
        setSavedGame(JSON.parse(stored));
      }
    } catch (e) {
      console.error('Failed to parse saved game metadata', e);
    }
  }, []);

  const handleCreatePrompt = () => {
    setJoinMode('create');
    setScreen('character_selection');
  };

  const handleJoinPrompt = () => {
    setJoinMode('join');
    setScreen('character_selection');
  };

  const handleConfirmCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!playerName.trim()) {
      setError('Por favor, digite seu nome.');
      return;
    }
    
    setLoading(true);
    setError(null);

    try {
      if (joinMode === 'create') {
        const res = await fetch('/api/game/new', { method: 'POST' });
        if (!res.ok) throw new Error('Falha ao criar sala de lobby.');
        const data = await res.json();
        setLobbyCode(data.lobby_code);
        setSessionId(data.session_id);
        setScreen('lobby');
      } else {
        if (!lobbyInput.trim() || lobbyInput.length !== 6) {
          throw new Error('Por favor, digite um código de sala válido com 6 caracteres.');
        }
        const code = lobbyInput.toUpperCase().trim();
        try {
          const res = await fetch(`/api/game/join/${code}`, { method: 'POST' });
          if (!res.ok) {
            throw new Error('Código inválido ou sessão expirada. Volte ao menu e peça um novo código.');
          }
          const data = await res.json();
          setLobbyCode(code);
          setSessionId(data.session_id);
          setScreen('lobby');
        } catch (fetchErr) {
          throw new Error('Código inválido ou sessão expirada. Volte ao menu e peça um novo código.');
        }
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadGame = async () => {
    if (!savedGame) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/game/load?session_id=${savedGame.session_id}`, { method: 'POST' });
      if (!res.ok) {
        if (res.status === 404) {
          localStorage.removeItem('pika_save');
          setSavedGame(null);
          throw new Error('Save não encontrado no servidor. Iniciando nova jornada.');
        }
        throw new Error('Falha ao carregar jogo');
      }
      const data = await res.json();
      setSessionId(data.session_id);
      setScreen('game_direct');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (screen === 'lobby' && sessionId) {
    return (
      <WebSocketProvider 
        sessionId={sessionId} 
        playerName={playerName} 
        playerClass={playerClass}
      >
        <LobbyOrGameWrapper lobbyCode={lobbyCode} isCreator={joinMode === 'create'} />
      </WebSocketProvider>
    );
  }

  if (screen === 'game_direct' && sessionId) {
    return (
      <WebSocketProvider sessionId={sessionId}>
        <GameContainer />
      </WebSocketProvider>
    );
  }

  if (screen === 'character_selection') {
    return (
      <div className="relative min-h-screen bg-[#07050a] flex flex-col items-center justify-center overflow-y-auto p-6 font-inter text-gray-100">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_50%,rgba(120,53,15,0.15),transparent_70%)] pointer-events-none" />
        
        <div className="w-full max-w-xl bg-gray-950 border border-gray-800 p-8 rounded-xl shadow-2xl relative z-10">
          <h2 className="font-cinzel text-center text-2xl font-black text-yellow-400 tracking-wider mb-6">
            {joinMode === 'create' ? 'CRIAR SALA DE AVENTURA' : 'ENTRAR NA JORNADA'}
          </h2>

          {error && <div className="mb-4 text-red-500 text-sm font-bold text-center">{error}</div>}

          <form onSubmit={handleConfirmCharacter} className="flex flex-col gap-6">
            {/* Lobby code input if joining */}
            {joinMode === 'join' && (
              <div className="flex flex-col gap-2">
                <label className="text-xs uppercase text-gray-400 font-bold tracking-widest">Código da Sala</label>
                <input
                  type="text"
                  maxLength={6}
                  value={lobbyInput}
                  onChange={(e) => setLobbyInput(e.target.value.toUpperCase())}
                  placeholder="EX: AETH42"
                  className="bg-gray-900 border border-gray-800 text-yellow-400 font-mono text-center text-xl py-3 px-4 rounded outline-none focus:border-yellow-500 transition-colors uppercase tracking-widest"
                  disabled={loading}
                />
              </div>
            )}

            {/* Name Input */}
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase text-gray-400 font-bold tracking-widest">Seu Nome de Aventureiro</label>
              <input
                type="text"
                maxLength={12}
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="Ex: Arthur"
                className="bg-gray-900 border border-gray-850 py-3 px-4 rounded text-gray-100 outline-none focus:border-yellow-500 transition-colors"
                disabled={loading}
              />
            </div>

            {/* Class Selection */}
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase text-gray-400 font-bold tracking-widest mb-2">Escolha sua Classe</label>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { id: 'GUERREIRO', name: '🛡️ Guerreiro', desc: 'Resiliência, espada e escudo.' },
                  { id: 'MAGO', name: '🔮 Mago', desc: 'Artes arcanas e dano espiritual.' },
                  { id: 'LADINO', name: '🗡️ Ladino', desc: 'Furtividade, trapaça e adagas.' },
                  { id: 'CLERIGO', name: '✨ Clérigo', desc: 'Luz divina, cura e milagres.' }
                ].map((cls) => (
                  <button
                    key={cls.id}
                    type="button"
                    onClick={() => setPlayerClass(cls.id)}
                    className={`p-4 rounded-lg border text-left flex flex-col gap-1 transition-all duration-300 ${
                      playerClass === cls.id
                        ? 'bg-yellow-950/20 border-yellow-500 text-yellow-400 shadow-[0_0_15px_rgba(234,179,8,0.1)]'
                        : 'bg-gray-900 border-gray-850 hover:border-gray-700 text-gray-400'
                    }`}
                  >
                    <span className="font-bold text-sm">{cls.name}</span>
                    <span className="text-[10px] leading-relaxed text-gray-500">{cls.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Confirm Button */}
            <button
              type="submit"
              disabled={loading}
              className="mt-4 py-4 px-8 bg-yellow-600 hover:bg-yellow-500 text-black font-cinzel font-bold tracking-widest text-sm rounded shadow-[0_0_20px_rgba(234,179,8,0.15)] transition-all duration-300 disabled:opacity-50"
            >
              {loading ? 'CONECTANDO...' : joinMode === 'create' ? 'CRIAR SALA E AGUARDAR' : 'ENTRAR NA SALA'}
            </button>

            {/* Back Button */}
            <button
              type="button"
              onClick={() => setScreen('menu')}
              className="py-2.5 text-center text-xs text-gray-500 hover:text-gray-300 transition-colors uppercase tracking-widest"
              disabled={loading}
            >
              ↩ Voltar ao Menu
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#07050a] flex flex-col items-center justify-center overflow-hidden font-inter">

      {/* Radial glow de fundo */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_50%,rgba(120,53,15,0.15),transparent_70%)] pointer-events-none" />

      {/* Partículas de névoa (CSS puro) */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_80%,rgba(88,28,135,0.08),transparent_50%)] pointer-events-none" />

      {/* Separador decorativo topo */}
      <div className="text-yellow-800/40 text-xs tracking-[0.5em] mb-8 font-cinzel">
        ✦ ✦ ✦
      </div>

      {/* Título principal */}
      <h1 className="font-cinzel font-black text-5xl md:text-7xl text-center tracking-[0.1em] mb-2"
          style={{ textShadow: '0 0 60px rgba(251,191,36,0.4), 0 0 120px rgba(251,191,36,0.15)' }}>
        <span className="text-yellow-400">AETHELGARD</span>
      </h1>

      <p className="font-cinzel text-gray-500 text-sm tracking-[0.4em] mb-2 uppercase">
        Crônicas de Aventura
      </p>

      {/* Separador decorativo */}
      <div className="flex items-center gap-4 my-8 w-64">
        <div className="flex-1 h-px bg-gradient-to-r from-transparent to-yellow-800/40" />
        <span className="text-yellow-700 text-xs">⚔</span>
        <div className="flex-1 h-px bg-gradient-to-l from-transparent to-yellow-800/40" />
      </div>

      {error && <div className="mb-4 text-red-500 text-sm font-bold z-10 text-center max-w-sm px-4">{error}</div>}

      {/* Botões */}
      <div className="flex flex-col gap-4 w-64 z-10">
        <button
          onClick={handleCreatePrompt}
          disabled={loading}
          className="py-4 px-8 bg-transparent border border-yellow-700/60 hover:border-yellow-500 text-yellow-400 hover:text-yellow-300 font-cinzel font-bold tracking-widest text-sm rounded transition-all duration-300 hover:shadow-[0_0_30px_rgba(234,179,8,0.2)] hover:bg-yellow-950/20 disabled:opacity-50 flex items-center justify-center animate-fade-in"
        >
          ▶ NOVA JORNADA
        </button>

        <button
          onClick={handleJoinPrompt}
          disabled={loading}
          className="py-4 px-8 bg-transparent border border-yellow-750 hover:border-yellow-500 text-yellow-400 hover:text-yellow-300 font-cinzel font-bold tracking-widest text-sm rounded transition-all duration-300 hover:shadow-[0_0_30px_rgba(234,179,8,0.15)] hover:bg-yellow-950/10 disabled:opacity-50 flex items-center justify-center"
        >
          👥 ENTRAR EM SESSÃO
        </button>

        <button
          onClick={loadGame}
          disabled={loading || !savedGame}
          className={`py-4 px-8 bg-transparent border ${
            savedGame
              ? 'border-yellow-700/60 hover:border-yellow-500 text-yellow-400 hover:text-yellow-300 hover:shadow-[0_0_30px_rgba(234,179,8,0.2)] hover:bg-yellow-950/20'
              : 'border-gray-700/60 text-gray-500 cursor-not-allowed'
          } font-cinzel font-bold tracking-widest text-sm rounded transition-all duration-300 disabled:opacity-50 flex flex-col items-center justify-center`}
        >
          {loading ? (
            <span>CARREGANDO...</span>
          ) : savedGame ? (
            <>
              <span>↩ CONTINUAR JORNADA</span>
              <span className="text-[10px] text-yellow-600/70 font-mono tracking-normal normal-case mt-1 text-center">
                {savedGame.player_name} · Cap. {savedGame.chapter} ({savedGame.location})
              </span>
            </>
          ) : (
            <span>↩ SEM SAVE ANTERIOR</span>
          )}
        </button>
      </div>

      {/* Versão */}
      <p className="absolute bottom-6 text-gray-700 text-xs font-mono tracking-widest">
        v1.0.0 · Web Edition
      </p>
    </div>
  );
}

export default function AppWithProviders() {
  return (
    <VisualEffectProvider>
      <App />
    </VisualEffectProvider>
  );
}
