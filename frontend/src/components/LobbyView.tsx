import React, { useState } from 'react';
import { useGame } from '../contexts/WebSocketProvider';

interface LobbyViewProps {
  lobbyCode: string;
  isCreator: boolean;
}

export const LobbyView: React.FC<LobbyViewProps> = ({ lobbyCode, isCreator }) => {
  const { lobbyState, sendAction, connected } = useGame();
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(lobbyCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleStartGame = () => {
    sendAction({ action: "START_GAME" });
  };

  const getEmojiForClass = (charClass: string) => {
    const c = charClass.toUpperCase();
    if (c === 'GUERREIRO') return '🛡️';
    if (c === 'MAGO') return '🔮';
    if (c === 'LADINO' || c === 'LADRÃO') return '🗡️';
    if (c === 'CLERIGO' || c === 'CLÉRIGO') return '✨';
    return '👤';
  };

  const getColorForClass = (charClass: string) => {
    const c = charClass.toUpperCase();
    if (c === 'GUERREIRO') return 'from-red-650 to-red-500 text-red-400';
    if (c === 'MAGO') return 'from-blue-650 to-blue-500 text-blue-400';
    if (c === 'LADINO' || c === 'LADRÃO') return 'from-emerald-650 to-emerald-500 text-emerald-400';
    if (c === 'CLERIGO' || c === 'CLÉRIGO') return 'from-yellow-650 to-yellow-500 text-yellow-400';
    return 'from-gray-700 to-gray-500 text-gray-400';
  };

  const players = lobbyState?.players || [];
  const leaderName = lobbyState?.leader_name || "Líder";

  return (
    <div className="relative min-h-screen bg-[#07050a] flex flex-col items-center justify-center p-6 font-inter text-gray-100 overflow-hidden">
      
      {/* Background Radial Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_50%,rgba(120,53,15,0.12),transparent_70%)] pointer-events-none" />

      {/* Main card */}
      <div className="w-full max-w-2xl bg-gray-950/80 border border-gray-800/80 rounded-xl p-8 shadow-2xl relative z-10 backdrop-blur-md">
        
        {/* Lobby Header */}
        <div className="text-center mb-8 border-b border-gray-800/60 pb-6">
          <span className="text-yellow-600 text-xs font-cinzel tracking-[0.3em] uppercase">Sala de Espera</span>
          <h1 className="font-cinzel font-black text-3xl md:text-4xl text-yellow-400 tracking-wide mt-2">
            Lobby de Aventura
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Reúna sua party de 2 a 4 jogadores antes de iniciar a jornada.
          </p>
        </div>

        {/* Lobby Code Display */}
        <div className="bg-gray-900/60 border border-gray-850 p-6 rounded-lg flex flex-col items-center justify-center mb-8 relative group">
          <span className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-1">Código da Sessão</span>
          <div className="flex items-center gap-4">
            <span className="font-mono text-3xl font-black tracking-widest text-yellow-400 select-all">
              {lobbyCode}
            </span>
            <button
              onClick={copyToClipboard}
              className="py-1.5 px-3 bg-gray-850 hover:bg-gray-800 border border-gray-700 text-xs text-gray-300 hover:text-white rounded transition-all duration-200"
            >
              {copied ? '✅ COPIADO!' : '📋 COPIAR'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Compartilhe este código com seus companheiros para que entrem no lobby.
          </p>
        </div>

        {/* Connected Players Section */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-cinzel text-sm text-gray-400 tracking-wider uppercase font-semibold">
              Membros Conectados ({players.length} / 4)
            </h2>
            {!connected && (
              <span className="text-red-400 text-xs animate-pulse font-mono">Conectando...</span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {players.map((player: any) => (
              <div 
                key={player.client_id}
                className="bg-gray-900/40 border border-gray-850 p-4 rounded-lg flex items-center gap-4 transition-all duration-300 hover:border-gray-750"
              >
                <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${getColorForClass(player.class)} flex items-center justify-center text-2xl shadow-inner shrink-0`}>
                  {getEmojiForClass(player.class)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-200 truncate">{player.name}</span>
                    {player.is_leader && (
                      <span className="text-[9px] bg-yellow-600/20 text-yellow-500 border border-yellow-500/30 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
                        Líder
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 block uppercase tracking-wider font-semibold mt-0.5">
                    {player.class}
                  </span>
                </div>
              </div>
            ))}

            {/* Empty slots placeholders */}
            {Array.from({ length: Math.max(0, 4 - players.length) }).map((_, i) => (
              <div 
                key={`empty-${i}`}
                className="border border-dashed border-gray-850 p-4 rounded-lg flex items-center gap-4 opacity-40 justify-center h-20 text-gray-600 italic text-sm"
              >
                Aguardando jogador...
              </div>
            ))}
          </div>
        </div>

        {/* Start Button / Status Display */}
        <div className="border-t border-gray-800/60 pt-6 flex flex-col items-center">
          {isCreator ? (
            <div className="w-full flex flex-col items-center gap-3">
              <button
                onClick={handleStartGame}
                disabled={!connected || players.length < 1}
                className="w-full py-4 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-black font-cinzel font-bold tracking-widest text-sm rounded shadow-[0_0_20px_rgba(234,179,8,0.15)] hover:shadow-[0_0_30px_rgba(234,179,8,0.25)] transition-all duration-300"
              >
                🚀 INICIAR AVENTURA
              </button>
              <p className="text-xs text-gray-500 italic text-center">
                Apenas você (Líder da party) pode dar início à jornada.
              </p>
            </div>
          ) : (
            <div className="w-full text-center bg-gray-900/20 border border-gray-850 p-4 rounded-lg">
              <div className="flex items-center justify-center gap-3">
                <div className="w-2.5 h-2.5 bg-yellow-500 rounded-full animate-ping" />
                <span className="text-sm font-semibold text-yellow-500/80 tracking-wide font-cinzel">
                  Aguardando o líder {leaderName} iniciar a aventura...
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
