import React from 'react';
import { useGame } from '../contexts/WebSocketProvider';
import { NarrativeView } from './NarrativeView';
import { CombatView } from './CombatView';
import { audioManager } from '../audio/AudioManager';

const CHAPTER_TITLES: Record<number, string> = {
  1: "Capítulo I: A Taverna de Millhaven",
  2: "Capítulo II: Sussurros das Profundezas",
  3: "Capítulo III: A Capela Corrompida",
  4: "Capítulo IV: O Cerco de Oakhaven",
  5: "Capítulo V: A Fortaleza do Vazio",
  6: "Capítulo VI: O Confronto Final"
};

export const GameContainer: React.FC = () => {
  const { gameState, uiContext, connected, error } = useGame();
  const [activeCombat, setActiveCombat] = React.useState<boolean | undefined>(undefined);
  const [fadeState, setFadeState] = React.useState<'in' | 'out'>('in');
  const [chapterOverlay, setChapterOverlay] = React.useState<number | null>(null);

  const prevChapterRef = React.useRef<number | null>(null);

  React.useEffect(() => {
    if (gameState?.current_chapter) {
      if (prevChapterRef.current !== null && gameState.current_chapter > prevChapterRef.current) {
        setChapterOverlay(gameState.current_chapter);
        const timer = setTimeout(() => {
          setChapterOverlay(null);
        }, 2500);
        return () => clearTimeout(timer);
      }
      prevChapterRef.current = gameState.current_chapter;
    }
  }, [gameState?.current_chapter]);

  React.useEffect(() => {
    if (gameState) {
      if (activeCombat === undefined) {
        setActiveCombat(gameState.in_combat);
      } else if (gameState.in_combat !== activeCombat) {
        setFadeState('out');
        const timer = setTimeout(() => {
          setActiveCombat(gameState.in_combat);
          setFadeState('in');
        }, 300);
        return () => clearTimeout(timer);
      }
    }
  }, [gameState?.in_combat, activeCombat]);

  // Monitor location and combat state to play BGM
  React.useEffect(() => {
    if (!gameState) return;

    if (gameState.in_combat) {
      const isBossFight = gameState.combat_state?.enemies.some((e: any) => {
        const name = e.name.toLowerCase();
        return name.includes('malakar') || name.includes('inquisidor') || name.includes('paladino') || name.includes('guardião') || name.includes('guardiao') || name.includes('elena') || name.includes('grum') || name.includes('vesper');
      });
      if (isBossFight) {
        audioManager.playMusic('boss');
      } else {
        audioManager.playMusic('combate');
      }
    } else {
      const loc = String(gameState.current_location || "").toLowerCase();
      if (loc.includes('taverna') || loc.includes('inicio') || loc.includes('inicial')) {
        audioManager.playMusic('taverna');
      } else if (loc.includes('vaelmoor')) {
        audioManager.playMusic('vaelmoor');
      } else if (loc.includes('floresta') || loc.includes('bosque') || loc.includes('estrada')) {
        audioManager.playMusic('floresta');
      } else if (loc.includes('templo') || loc.includes('fortaleza') || loc.includes('santuario')) {
        audioManager.playMusic('templo');
      } else if (loc.includes('caverna') || loc.includes('millhaven') || loc.includes('corrompidas') || loc.includes('acampamento')) {
        audioManager.playMusic('templo');
      } else {
        audioManager.playMusic('floresta');
      }
    }
  }, [gameState?.current_location, gameState?.in_combat, gameState?.combat_state?.enemies]);

  // Stop music and play defeat SFX on game over
  React.useEffect(() => {
    if (uiContext?.type === 'GAME_OVER') {
      audioManager.stopMusic();
      audioManager.playSFX('DEFEAT');
    }
  }, [uiContext?.type]);

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-red-950 text-red-500 font-bold p-4">
        <p>ERRO DE CONEXÃO: {error}</p>
      </div>
    );
  }

  if (!connected) {
    return (
      <div className="flex h-screen items-center justify-center bg-black text-gray-500">
        <p className="animate-pulse">Estabelecendo elo com a Engine...</p>
      </div>
    );
  }

  if (uiContext?.type === 'GAME_OVER') {
    return (
      <div className="relative min-h-screen bg-[#07050a] flex flex-col items-center justify-center overflow-hidden font-inter">
        {/* Glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_50%,rgba(220,38,38,0.15),transparent_70%)] pointer-events-none" />
        
        <h1 className="font-cinzel font-black text-5xl md:text-7xl text-center tracking-[0.1em] mb-4 text-red-600 animate-pulse"
            style={{ textShadow: '0 0 60px rgba(220,38,38,0.4), 0 0 120px rgba(220,38,38,0.15)' }}>
          FIM DE JOGO
        </h1>
        
        <p className="font-cinzel text-gray-400 text-sm tracking-[0.4em] mb-8 uppercase max-w-md text-center leading-relaxed">
          {uiContext.prompt || "Sua jornada terminou de forma trágica..."}
        </p>

        <button
          onClick={() => window.location.reload()}
          className="py-4 px-8 bg-transparent border border-red-700/60 hover:border-red-500 text-red-500 hover:text-red-400 font-cinzel font-bold tracking-widest text-sm rounded transition-all duration-300 hover:shadow-[0_0_30px_rgba(220,38,38,0.2)] hover:bg-red-950/20"
        >
          ↩ RETORNAR AO MENU
        </button>
      </div>
    );
  }

  if (!gameState && !uiContext) {
    return (
      <div className="flex h-screen items-center justify-center bg-black text-gray-500">
        <p className="animate-pulse">Sincronizando universo (GameState)...</p>
      </div>
    );
  }

  console.log('in_combat:', gameState?.in_combat, 'combat_state:', gameState?.combat_state);

  return (
    <div className="w-full h-screen bg-gray-950 text-gray-100 flex flex-col font-inter selection:bg-yellow-500 selection:text-black">
      {/* Main Content Area - Router based on in_combat */}
      <main className="flex-1 overflow-hidden relative flex flex-col">
        <div
          key={activeCombat ? 'combat' : 'narrative'}
          className={`absolute inset-0 transition-all duration-300 ${
            fadeState === 'in' ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
          }`}
        >
          {activeCombat ? <CombatView /> : <NarrativeView />}
        </div>
      </main>

      {chapterOverlay !== null && (
        <div className="fixed inset-0 bg-black z-[9999] flex flex-col items-center justify-center animate-fade-in transition-all duration-500">
          <div className="text-center p-8 border border-yellow-600/30 bg-yellow-950/10 rounded-xl max-w-lg shadow-[0_0_80px_rgba(243,156,18,0.15)]">
            <p className="text-yellow-600 font-cinzel tracking-[0.3em] uppercase text-xs mb-2">Jornada</p>
            <h1 className="text-3xl md:text-5xl font-cinzel font-black tracking-widest text-yellow-400"
                style={{ textShadow: '0 0 40px rgba(243,156,18,0.6)' }}>
              {CHAPTER_TITLES[chapterOverlay] || `Capítulo ${chapterOverlay}`}
            </h1>
          </div>
        </div>
      )}
    </div>
  );
};
