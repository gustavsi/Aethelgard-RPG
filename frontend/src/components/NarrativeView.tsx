import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useGame } from '../contexts/WebSocketProvider';

const TypewriterText: React.FC<{ text: string; isAscii?: boolean }> = ({ text, isAscii }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    if (isAscii || text.length > 500) {
      setDisplayedText(text);
      return;
    }

    let i = 0;
    setDisplayedText('');
    const interval = setInterval(() => {
      setDisplayedText(prev => prev + text.charAt(i));
      i++;
      if (i >= text.length) {
        clearInterval(interval);
      }
    }, 10); // 10ms delay per character

    return () => clearInterval(interval);
  }, [text, isAscii]);

  return <>{displayedText}</>;
};

export const NarrativeView: React.FC = () => {
  const { uiContext, narrativeLog, clearNarrative, sendAction, gameState, isLeader, systemNotification } = useGame();
  const myClientId = useGame().myClientId;
  const myPlayer: any = gameState?.party?.find((p: any) => p.client_id === myClientId) 
      || gameState?.party?.[0] 
      || gameState?.player;
  const [textInput, setTextInput] = useState('');
  const logEndRef = useRef<HTMLDivElement>(null);

  const isWaitingMenu = uiContext?.prompt?.includes("Aguardando") || 
                        uiContext?.prompt?.includes("pronto") ||
                        uiContext?.prompt?.includes("Inventário") ||
                        uiContext?.prompt?.includes("Estoque");

  const getScenarioBackground = (location: string | undefined) => {
    if (!location) return null;
    const l = location.toLowerCase();
    if (l.includes('vaelmoor')) return '/cenario_vaelmoor.jpg';
    if (l.includes('floresta')) return '/cenario_floresta.jpg';
    if (l.includes('caverna')) return '/cenario_caverna.jpg';
    if (l.includes('templo')) return '/cenario_templo.jpg';
    if (l.includes('cabana')) return '/cenario_cabana.jpg';
    if (l.includes('oakhaven')) return '/cenario_oakhaven.jpg';
    if (l.includes('bosque')) return '/cenario_bosque_sagrado.jpg';
    if (l.includes('estrada')) return '/cenario_estrada_antiga.jpg';
    if (l.includes('tutorial')) return '/cenario_floresta.jpg';
    if (l.includes('taverna') || l.includes('inicio') || l.includes('inicial')) return '/cenario_taverna.jpg';
    if (l.includes('millhaven')) return '/cenario_millhaven.jpg';
    if (l.includes('corrompidas') || l.includes('acampamento') || l.includes('santuario') || l.includes('fortaleza')) return '/cenario_terras_corrompidas.jpg';
    if (l.includes('cerco') || l.includes('combate_cerco')) return '/cenario_cerco_oakhaven.jpg';
    return null;
  };

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [narrativeLog, uiContext]);

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim() !== '') {
      sendAction({ action: "INPUT", value: textInput });
      setTextInput('');
    }
  };

  const handleOptionClick = (key: string) => {
    sendAction({ action: "MENU_CHOICE", value: key });
  };

  const classifyNarrative = (text: string): string => {
    if (text.includes('<!--ascii-->'))
      return 'ascii';
    if (text.startsWith('🔊') || (text.startsWith('*') && text.endsWith('*')))
      return 'sound';
    if (text.includes('"') || text.includes('"'))
      return 'dialogue';
    if (text.startsWith('===') || text.startsWith('---') || text.startsWith('──'))
      return 'title';
    if (text.startsWith('✨') || text.startsWith('⚔') || text.startsWith('💀'))
      return 'event';
    return 'narration';
  };

  const narrativeStyles: Record<string, string> = {
    sound:    'text-purple-300 italic text-sm opacity-80',
    dialogue: 'text-yellow-100 pl-4 border-l-2 border-yellow-700/50 my-1',
    title:    'text-yellow-400 font-cinzel font-bold text-center text-lg mt-4 mb-2 tracking-wider',
    event:    'text-amber-300 font-semibold my-1',
    narration:'text-gray-300 leading-loose',
    ascii:    'font-mono text-[9px] sm:text-[10px] leading-tight whitespace-pre overflow-x-auto text-emerald-400 bg-black/40 p-4 border border-gray-800/60 rounded my-2 block'
  };

  const bgImage = useMemo(() => {
    return getScenarioBackground(gameState?.current_location);
  }, [gameState?.current_location]);

  if (!uiContext && narrativeLog.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center h-full bg-gray-950">
        <p className="animate-pulse text-gray-500">Aguardando mestre do jogo...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-row flex-1 overflow-hidden h-full bg-gray-900 border border-gray-800 shadow-2xl rounded-lg">
      
      {/* COLUNA ESQUERDA (60% da largura) — texto do jogo */}
      <div className="w-[60%] flex flex-col h-full bg-gray-900 overflow-hidden relative">
        {systemNotification && (
          <div className="absolute top-0 left-0 right-0 z-40 bg-yellow-600 text-black py-2.5 px-4 font-bold text-center flex items-center justify-center gap-2 shadow-lg backdrop-blur-sm transition-all duration-300">
            {systemNotification}
          </div>
        )}

        {/* Imagem de background sutil na área de texto */}
        {bgImage && (
          <div 
            className="absolute inset-0 z-0 opacity-[0.03] bg-cover bg-center pointer-events-none"
            style={{ backgroundImage: `url(${bgImage})` }}
          />
        )}

        {/* Log narrativo com scroll */}
        <div className="flex-1 overflow-y-auto p-6 whitespace-pre-wrap text-gray-300 leading-relaxed text-lg scrollbar-thin scrollbar-thumb-gray-700 relative z-10">
          {narrativeLog.map((log, index) => {
            const isAscii = classifyNarrative(log) === 'ascii';
            const cleanLog = isAscii ? log.replace('<!--ascii-->', '') : log;
            const isLast = index === narrativeLog.length - 1;
            return (
              <div key={index} className={`mb-2 ${narrativeStyles[classifyNarrative(log)] || 'text-gray-300'}`}>
                {isLast ? (
                  <TypewriterText text={cleanLog} isAscii={isAscii} />
                ) : (
                  cleanLog
                )}
              </div>
            );
          })}
          {uiContext?.prompt && (
            <div className="mt-6 text-yellow-500 font-bold">{uiContext.prompt}</div>
          )}
          <div ref={logEndRef} />
        </div>

        {/* Botões de escolha no rodapé */}
        {uiContext && (
          <div className="shrink-0 p-6 bg-gray-950 border-t border-gray-800 overflow-y-auto max-h-[40vh] relative z-10">
            {!isLeader && !isWaitingMenu ? (
              <div className="text-gray-500 text-center py-6 italic flex items-center justify-center gap-2">
                ⏳ O líder está decidindo o próximo passo da party...
              </div>
            ) : uiContext.options ? (
              <div className="grid grid-cols-1 gap-2.5 overflow-y-auto max-h-[45vh]">
                {Object.entries(uiContext.options).map(([key, value]) => (
                  <button
                    key={key}
                    onClick={() => handleOptionClick(key)}
                    className="bg-gray-800 hover:bg-gray-700 text-left h-auto py-3.5 px-5 border border-gray-700 hover:border-yellow-500 rounded transition-all text-yellow-500 whitespace-normal hover:shadow-[0_0_12px_rgba(234,179,8,0.15)]"
                  >
                    <span className="font-bold mr-3 text-gray-500">[{key}]</span>
                    {value}
                  </button>
                ))}
              </div>
            ) : uiContext?.subtype === 'PRESS_ANY_KEY' ? (
              <button
                onClick={() => sendAction({ action: "INPUT", value: " " })}
                className="w-full py-5 bg-gray-800 hover:bg-gray-700 border border-gray-600 hover:border-yellow-500 rounded text-yellow-500 font-bold text-lg tracking-widest transition-all hover:shadow-[0_0_15px_rgba(234,179,8,0.25)]"
              >
                ▶ Pressionar para continuar
              </button>
            ) : (
              <form onSubmit={handleTextSubmit} className="flex gap-3">
                <input
                  type="text"
                  autoFocus
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="O que você faz?"
                  className="flex-1 bg-gray-800 border border-gray-700 px-5 py-3.5 rounded text-gray-100 outline-none focus:border-yellow-500 transition-colors"
                  disabled={uiContext.type === 'GAME_OVER' || uiContext.type === 'ERROR'}
                />
                <button 
                  type="submit"
                  disabled={uiContext.type === 'GAME_OVER' || uiContext.type === 'ERROR' || !textInput.trim()}
                  className="px-8 py-3.5 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 disabled:hover:bg-yellow-600 text-black font-bold rounded transition-colors"
                >
                  Enviar
                </button>
              </form>
            )}
          </div>
        )}
      </div>

      {/* COLUNA DIREITA (40% da largura) — painel contextual fixo */}
      <div className="w-[40%] flex flex-col border-l border-gray-800 bg-gray-950 p-6 overflow-y-auto z-10 shrink-0">
        
        {/* Imagem do cenário atual ocupando ~50% do espaço vertical visual */}
        <div className="flex flex-col h-[280px] shrink-0 mb-6">
          <div 
            key={gameState?.current_location}
            className="flex-1 rounded-lg border border-gray-800 bg-cover bg-center shadow-lg relative overflow-hidden bg-gray-900 transition-all duration-700"
            style={{ backgroundImage: bgImage ? `url(${bgImage})` : 'none' }}
          >
            {!bgImage && (
              <div className="absolute inset-0 flex items-center justify-center text-gray-600 italic text-sm">
                Sem Imagem de Cenário
              </div>
            )}
          </div>
          <div className="text-center mt-3 font-cinzel font-bold text-gray-400 text-xs tracking-widest uppercase">
            📍 {gameState?.current_location || "Aethelgard"}
          </div>
        </div>

        {/* Painel de status expandido */}
        <div className="flex flex-col gap-5 justify-start">
          
          {/* Nome + classe do personagem */}
          <div className="border-b border-gray-800 pb-3">
            <h2 className="font-cinzel font-black text-xl text-yellow-400 tracking-wide truncate">
              {myPlayer?.name || "Aventureiro"}
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Nível {myPlayer?.level || 1} · {myPlayer?.char_class || myPlayer?.class || "Nenhuma"}
            </p>
          </div>

          {/* Barras de HP e MP */}
          <div className="flex flex-col gap-3">
            {/* HP */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-xs">
                <span className="text-red-400 font-bold flex items-center gap-1">
                  <span>❤</span> HP
                </span>
                <span className="text-red-400 font-mono text-xs">
                  {myPlayer?.hp || 0} / {myPlayer?.max_hp || 0}
                </span>
              </div>
              <div className="h-3 bg-gray-900 rounded-full overflow-hidden border border-gray-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-red-800 to-red-500 transition-all duration-500"
                  style={{ width: `${myPlayer ? (myPlayer.hp / myPlayer.max_hp) * 100 : 100}%` }}
                />
              </div>
            </div>

            {/* MP */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-xs">
                <span className="text-blue-400 font-bold flex items-center gap-1">
                  <span>✦</span> MP
                </span>
                <span className="text-blue-400 font-mono text-xs">
                  {myPlayer?.mp || 0} / {myPlayer?.max_mp || 0}
                </span>
              </div>
              <div className="h-3 bg-gray-900 rounded-full overflow-hidden border border-gray-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-800 to-blue-500 transition-all duration-500"
                  style={{ width: `${myPlayer ? (myPlayer.mp / myPlayer.max_mp) * 100 : 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Ouro & Capítulo */}
          <div className="flex justify-between items-center bg-gray-900/60 p-3 rounded-lg border border-gray-850 text-sm">
            <span className="text-yellow-500 font-mono flex items-center gap-1.5">
              💰 <span className="font-bold">{myPlayer?.gold || 0}G</span>
            </span>
            <span className="text-gray-400 font-cinzel font-semibold tracking-wider">
              Capítulo {gameState?.current_chapter || 1}
            </span>
          </div>

          {/* Companheiro Ativo */}
          {gameState?.player?.companion && (
            <div className="bg-gray-900/30 border border-gray-800 p-4 rounded-lg flex flex-col gap-1.5">
              <div className="flex justify-between items-center border-b border-gray-800/50 pb-1">
                <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Companheiro</span>
                <span className="text-[10px] text-emerald-400 font-bold">Ativo</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-gray-200">{gameState.player.companion.name}</span>
                <span className="text-xs text-gray-500 italic mt-0.5">{gameState.player.companion.description}</span>
              </div>
            </div>
          )}

          {/* Flags de consequência (apenas se houver alguma true) */}
          {gameState?.flags && Object.entries(gameState.flags).some(([_, val]) => val === true) && (
            <div className="flex flex-col gap-2 border-t border-gray-805 pt-4">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Decisões e Consequências</span>
              <div className="flex flex-wrap gap-2 mt-1">
                {Object.entries(gameState.flags)
                  .filter(([_, val]) => val === true)
                  .map(([key]) => {
                    const labelMap: Record<string, string> = {
                      poupou_ogro: "⚔️ Ogro Poupado",
                      ajudou_goblin: "🌿 Goblin Ajudado",
                      ajudou_sobreviventes: "👥 Sobreviventes Ajudados",
                      millhaven_salva: "⛪ Millhaven Salva",
                      oakhaven_defendida: "🛡️ Oakhaven Defendida",
                      lacre_sombrio: "🌀 Lacre Sombrio",
                      guardou_pergaminho: "📜 Guardou Pergaminho",
                      roubou_cabana: "🏚️ Cabana Saqueada"
                    };
                    const displayLabel = labelMap[key];
                    if (!displayLabel) return null;
                    return (
                      <span 
                        key={key} 
                        className="text-[10px] font-medium bg-gray-900 border border-gray-800 text-yellow-500/80 px-2 py-0.5 rounded-full"
                      >
                        {displayLabel}
                      </span>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Botão de Estoque da Party Compartilhado */}
      <button onClick={() => sendAction({action: "OPEN_PARTY_STOCK"})}
          className="fixed bottom-4 right-4 z-50 bg-gray-800 border border-purple-700 
                     text-purple-400 px-4 py-2 rounded font-cinzel text-sm
                     hover:border-purple-400 transition-all shadow-lg hover:shadow-[0_0_15px_rgba(168,85,247,0.2)]">
          🧪 Estoque
      </button>

      {/* Botão de Inventário Individual Paralelo */}
      <button onClick={() => sendAction({action: "OPEN_INVENTORY"})}
          className="fixed bottom-4 right-32 z-50 bg-gray-800 border border-yellow-700 
                     text-yellow-400 px-4 py-2 rounded font-cinzel text-sm
                     hover:border-yellow-400 transition-all shadow-lg hover:shadow-[0_0_15px_rgba(234,179,8,0.2)]">
          🎒 Inventário
      </button>

      {/* Botão de Limpar Log Local */}
      <button onClick={clearNarrative}
          className="fixed bottom-4 right-64 z-50 bg-gray-800 border border-red-700 
                     text-red-400 px-4 py-2 rounded font-cinzel text-sm
                     hover:border-red-400 transition-all shadow-lg hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]">
          🧹 Limpar Log
      </button>
    </div>
  );
};
