import React, { useRef, useEffect } from 'react';
import { useGame } from '../contexts/WebSocketProvider';
import { useVisualEffects } from '../contexts/VisualEffectProvider';
import { ProjectileLayer } from './ProjectileLayer';
import audioManager from '../audio/AudioManager';

interface EnemyIntent {
  category: string;
  label: string;
  uninterruptible: boolean;
  interrupted: boolean;
}

interface Enemy {
  idx: number;
  name: string;
  hp: number;
  max_hp: number;
  mp: number;
  max_mp: number;
  alive: boolean;
  defending: boolean;
  status: string[];
  intent?: EnemyIntent | null;
}

const INTENT_STYLE: Record<string, string> = {
  attack: 'bg-red-900/70 text-red-200 border-red-600/60',
  cast: 'bg-violet-900/70 text-violet-200 border-violet-500/60',
  guard: 'bg-sky-900/70 text-sky-200 border-sky-500/60',
  special: 'bg-amber-900/70 text-amber-200 border-amber-500/60',
  none: 'bg-gray-800/70 text-gray-400 border-gray-600/50',
};

const INTENT_ICON: Record<string, string> = {
  attack: '⚔️',
  cast: '✨',
  guard: '🛡️',
  special: '☠️',
  none: '·',
};

const getHeroSprite = (playerClass: any) => {
  const c = String(playerClass || "").toLowerCase();
  if (c?.includes('guerreiro')) return '/hero_guerreiro.jpg';
  if (c?.includes('mago')) return '/hero_mago.jpg';
  if (c?.includes('ladino') || c?.includes('ladrao')) return '/hero_ladrao.jpg';
  if (c?.includes('clerigo')) return '/hero_clerigo.jpg';
  return '/hero.jpg';
};

const getSubclassAuraClass = (talents: string[] | undefined): string => {
  if (!talents) return "";
  const t = talents;
  // Warrior: Colosso 2 + Berserker 2 -> Juggernaut Calejado
  if (t.includes("guerreiro_colosso_2") && t.includes("guerreiro_berserker_2")) {
    return "ring-4 ring-red-600 shadow-[0_0_20px_#ef4444] animate-pulse";
  }
  // Mage: Piromante 2 + Criomante 2 -> Tempestade de Gelo
  if (t.includes("mago_piromante_2") && t.includes("mago_criomante_2")) {
    return "ring-4 ring-cyan-400 shadow-[0_0_20px_#06b6d4] animate-pulse";
  }
  // Cleric: Santo 2 + Inquisidor 2 -> Cruzado
  if (t.includes("clerigo_santo_2") && t.includes("clerigo_inquisidor_2")) {
    return "ring-4 ring-yellow-400 shadow-[0_0_20px_#fbbf24] animate-pulse";
  }
  // Ranger: Caçador 2 + Sentinela 2 -> Sentinela Oportunista
  if (t.includes("arqueiro_cacador_2") && t.includes("arqueiro_sentinela_2")) {
    return "ring-4 ring-emerald-500 shadow-[0_0_20px_#10b981] animate-pulse";
  }
  // Rogue: Assassino 2 + Trapaceiro 2 -> Dança das Sombras
  if (t.includes("ladino_assassino_2") && t.includes("ladino_trapaceiro_2")) {
    return "ring-4 ring-purple-600 shadow-[0_0_20px_#8b5cf6] animate-pulse";
  }
  return "";
};

export const CombatView: React.FC = () => {
  const { gameState, uiContext, sendAction, isLeader, myClientId } = useGame();
  const combatState = gameState?.combat_state;
  const logEndRef = useRef<HTMLDivElement>(null);
  console.log('PARTY DATA:', gameState?.party, 'MY_CLIENT_ID:', myClientId);

  const { effects, triggerEffect } = useVisualEffects();
  const weather = gameState?.flags?.weather || "Ensolarado";
  const timeOfDay = gameState?.flags?.time_of_day || "Dia";

  const prevEnemyHpsRef = useRef<Record<number, number>>({});
  const prevPlayerHpRef = useRef<number>(gameState?.player?.hp || 0);
  const prevLevelRef = useRef<number>(gameState?.player?.level || 1);
  const prevPartyHpsRef = useRef<Record<string, number>>({});

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [combatState?.logs]);

  // Monitor level up
  useEffect(() => {
    if (gameState?.player) {
      if (gameState.player.level > prevLevelRef.current) {
        triggerEffect({
          type: 'text',
          targetId: 'player',
          text: 'LEVEL UP!',
          color: 'gold',
          duration: 2000
        });
        triggerEffect({
          type: 'screen_flash',
          targetId: 'global',
          duration: 500,
          color: 'heal',
        });
        audioManager.playSFX('LEVEL_UP');
      }
      prevLevelRef.current = gameState.player.level;
    }
  }, [gameState?.player?.level, triggerEffect]);

  // Monitor party HP → local VFX + hit SFX (backend VFX may lag / miss multiplayer)
  useEffect(() => {
    if (gameState?.party) {
      gameState.party.forEach((member: any) => {
        const id = member.client_id || 'leader';
        const prevHp = prevPartyHpsRef.current[id];
        if (prevHp !== undefined && member.hp !== prevHp) {
          const delta = member.hp - prevHp;
          if (delta < 0) {
            const dmg = Math.abs(delta);
            const isCrit = dmg >= Math.max(12, (member.max_hp || 50) * 0.18);
            triggerEffect({ type: 'shake', targetId: `party_${id}`, duration: 420 });
            triggerEffect({ type: 'impact', targetId: `party_${id}`, duration: 420, isCrit });
            triggerEffect({
              type: 'damage_number',
              targetId: `party_${id}`,
              amount: dmg,
              isCrit,
              duration: 1000,
              text: `-${dmg}`,
            });
            triggerEffect({
              type: 'screen_flash',
              targetId: 'global',
              duration: isCrit ? 380 : 280,
              color: isCrit ? 'crit' : 'damage',
            });
            audioManager.playHit(isCrit, Math.min(1.4, 0.7 + dmg / 40));
          } else if (delta > 0) {
            triggerEffect({ type: 'heal_glow', targetId: id, duration: 1100 });
            triggerEffect({
              type: 'heal_number',
              targetId: `party_${id}`,
              amount: delta,
              duration: 1000,
              text: `+${delta}`,
            });
            triggerEffect({
              type: 'screen_flash',
              targetId: 'global',
              duration: 300,
              color: 'heal',
            });
            audioManager.playSFX('heal_chime', { intensity: 0.85 });
          }
        }
        prevPartyHpsRef.current[id] = member.hp;
      });
    } else if (gameState?.player) {
      const prevHp = prevPlayerHpRef.current;
      if (prevHp !== undefined && gameState.player.hp !== prevHp) {
        const delta = gameState.player.hp - prevHp;
        if (delta < 0) {
          const dmg = Math.abs(delta);
          const isCrit = dmg >= 12;
          triggerEffect({ type: 'shake', targetId: 'party_leader', duration: 420 });
          triggerEffect({ type: 'impact', targetId: 'party_leader', duration: 420, isCrit });
          triggerEffect({
            type: 'damage_number',
            targetId: 'party_leader',
            amount: dmg,
            isCrit,
            duration: 1000,
            text: `-${dmg}`,
          });
          audioManager.playHit(isCrit);
        } else if (delta > 0) {
          triggerEffect({ type: 'heal_glow', targetId: 'leader', duration: 1100 });
          triggerEffect({
            type: 'heal_number',
            targetId: 'party_leader',
            amount: delta,
            duration: 1000,
            text: `+${delta}`,
          });
        }
      }
      prevPlayerHpRef.current = gameState.player.hp;
    }
  }, [gameState?.party, gameState?.player?.hp, triggerEffect]);

  // Monitor enemy HP → impact + floating numbers + SFX
  useEffect(() => {
    if (combatState?.enemies) {
      combatState.enemies.forEach((enemy: Enemy) => {
        const prevHp = prevEnemyHpsRef.current[enemy.idx];
        if (prevHp !== undefined && enemy.hp !== prevHp) {
          const delta = enemy.hp - prevHp;
          if (delta < 0) {
            const dmg = Math.abs(delta);
            const isCrit = dmg >= Math.max(15, (enemy.max_hp || 80) * 0.12);
            const tid = `enemy_${enemy.idx}`;
            triggerEffect({ type: 'shake', targetId: tid, duration: 420 });
            triggerEffect({ type: 'impact', targetId: tid, duration: 420, isCrit });
            triggerEffect({
              type: 'damage_number',
              targetId: tid,
              amount: dmg,
              isCrit,
              duration: 1000,
              text: `-${dmg}`,
            });
            if (isCrit) {
              triggerEffect({ type: 'crit_burst', targetId: tid, duration: 550 });
              triggerEffect({
                type: 'screen_flash',
                targetId: 'global',
                duration: 320,
                color: 'crit',
              });
            }
            audioManager.playHit(isCrit, Math.min(1.5, 0.75 + dmg / 50));
          } else if (delta > 0) {
            triggerEffect({ type: 'heal_glow', targetId: `enemy_${enemy.idx}`, duration: 1000 });
          }
        }
        prevEnemyHpsRef.current[enemy.idx] = enemy.hp;
      });
    }
  }, [combatState?.enemies, triggerEffect]);

  if (!combatState) {
    return <div className="text-red-500 flex justify-center items-center h-full animate-pulse font-bold">Carregando dados de combate...</div>;
  }

  const handleOptionClick = (key: string) => {
    audioManager.playUiClick();
    sendAction({ action: "MENU_CHOICE", value: key });
  };

  const getEnemySprite = (name: string) => {
    const n = name.toLowerCase();
    if (n.includes('grum')) return '/contramestre_grum.jpg';
    if (n.includes('pirata')) return '/pirata_mare_negra.jpg';
    if (n.includes('vesper')) return '/vesper.jpg';
    if (n.includes('malakar') || n.includes('lorde')) return '/malakar.jpg';
    if (n.includes('golem')) return '/golem_pedra.jpg';
    if (n.includes('inquisidor')) return '/inquisidor_sombrio.jpg';
    if (n.includes('verme')) return '/verme_rocha.jpg';
    if (n.includes('morcego')) return '/morcego_gigante.jpg';
    if (n.includes('portal') || n.includes('guardião do portal') || n.includes('guardiao do portal')) return '/guardiao_portal.jpg';
    if (n.includes('guardião') || n.includes('guardiao')) return '/guardiao_floresta.jpg';
    if (n.includes('lobo')) return '/lobo_floresta.jpg';
    if (n.includes('ogro')) return '/ogro.jpg';
    if (n.includes('elena')) return '/elena_boss.jpg';
    if (n.includes('salteador') || n.includes('ladrão') || n.includes('bandit')) return '/salteador.jpg';
    if (n.includes('goblin')) return '/goblin.jpg';
    if (n.includes('ent') || n.includes('árvore')) return '/ent_corrompido.jpg';
    if (n.includes('paladino')) return '/paladino_corrompido.jpg';
    if (n.includes('assassino')) return '/assassino_malakar.jpg';
    return null; // Fallback
  };

  const getEnemyFallbackEmoji = (name: string) => {
    const n = name.toLowerCase();
    if (n.includes('lobo')) return '🐺';
    if (n.includes('goblin')) return '👺';
    if (n.includes('ent') || n.includes('árvore') || n.includes('guardião')) return '🌳';
    if (n.includes('aranha')) return '🕷️';
    if (n.includes('cultista')) return '🧙‍♂️';
    if (n.includes('morcego')) return '🦇';
    if (n.includes('verme')) return '🪱';
    if (n.includes('golem')) return '🪨';
    return '💀';
  };

  const classifyLog = (log: string): string => {
    const l = log.toLowerCase();
    if (l.includes('crítico') || l.includes('critico')) return 'crit';
    if (l.includes('dano') || l.includes('causou') || l.includes('sofreu') || l.includes('sangra') || l.includes('queima')) return 'damage';
    if (l.includes('curou') || l.includes('recuperou') || l.includes('regenerou')) return 'heal';
    if (l.includes('fugiu') || l.includes('escapou') || l.includes('foge')) return 'fled';
    if (l.includes('veneno') || l.includes('efeito') || l.includes('status')) return 'status';
    if (l.includes('bloqueou') || l.includes('defendeu') || l.includes('esquivou') || l.includes('desviou')) return 'block';
    return 'neutral';
  };

  const logColors: Record<string, string> = {
    damage: 'text-red-400',
    crit:   'text-orange-300 font-bold',
    heal:   'text-green-400',
    fled:   'text-yellow-400 italic',
    status: 'text-purple-400',
    block:  'text-blue-400',
    neutral:'text-gray-400',
  };

  const getActionStyle = (_key: string, value: string): string => {
    const v = value.toLowerCase();
    if (v.includes('atac')) return 'border-red-800 text-red-400 hover:border-red-500 hover:bg-red-950/30';
    if (v.includes('habil') || v.includes('magia') || v.includes('skill'))
      return 'border-purple-800 text-purple-400 hover:border-purple-500 hover:bg-purple-950/30';
    if (v.includes('item') || v.includes('poção') || v.includes('pocao'))
      return 'border-blue-800 text-blue-400 hover:border-blue-500 hover:bg-blue-950/30';
    if (v.includes('defende') || v.includes('bloquei'))
      return 'border-yellow-800 text-yellow-500 hover:border-yellow-500 hover:bg-yellow-950/30';
    if (v.includes('fug') || v.includes('escap'))
      return 'border-gray-700 text-gray-500 hover:border-gray-500 hover:bg-gray-900/30';
    return 'border-gray-700 text-gray-300 hover:border-gray-500';
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 border border-red-900/50 shadow-[0_0_50px_rgba(220,38,38,0.1)] rounded-xl overflow-hidden max-w-5xl mx-auto">
      
      {/* Barra de Ações Rápidas (Topo do Combate) */}
      <div className="bg-gray-950 px-4 py-2 border-b border-red-900/30 flex justify-between items-center z-20">
        <span className="text-[10px] text-red-500 font-cinzel tracking-widest font-bold">⚔️ COMBATE COOPERATIVO</span>
        <div className="flex gap-2">
          <button onClick={() => sendAction({action: "OPEN_TALENTS"})}
              className="bg-gray-900 border border-green-750 hover:border-green-500 text-green-400 px-3 py-1 rounded font-cinzel text-[10px] transition-all shadow hover:shadow-[0_0_10px_rgba(34,197,94,0.15)]">
              🌳 Talentos
          </button>
          <button onClick={() => sendAction({action: "OPEN_INVENTORY"})}
              className="bg-gray-900 border border-yellow-750 hover:border-yellow-500 text-yellow-400 px-3 py-1 rounded font-cinzel text-[10px] transition-all shadow hover:shadow-[0_0_10px_rgba(234,179,8,0.15)]">
              🎒 Inventário
          </button>
          <button onClick={() => sendAction({action: "OPEN_PARTY_STOCK"})}
              className="bg-gray-900 border border-purple-750 hover:border-purple-500 text-purple-400 px-3 py-1 rounded font-cinzel text-[10px] transition-all shadow hover:shadow-[0_0_10px_rgba(168,85,247,0.15)]">
              🧪 Estoque
          </button>
        </div>
      </div>

      {/* 1. Combat Log (Topo) */}
      <div className="h-48 bg-gray-950 border-b border-red-900/30 p-4 overflow-y-auto font-mono text-sm shadow-inner scrollbar-thin scrollbar-thumb-red-900">
        {combatState.logs.map((log: string, idx: number) => (
          <div key={idx} className={`mb-1 animate-fade-in text-sm font-mono ${logColors[classifyLog(log)] || 'text-gray-400'}`}>
            {log}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
             {/* 2. Arena */}
      <div className="flex-1 flex flex-row justify-between items-end px-8 md:px-20 pb-8 relative overflow-hidden min-h-[360px]">
        {/* Weather & Time Overlays */}
        {timeOfDay === "Noite" && (
          <div className="absolute inset-0 bg-blue-950/20 mix-blend-multiply pointer-events-none z-10" />
        )}
        {timeOfDay === "Noite" && (
          <div className="absolute inset-0 bg-black/25 pointer-events-none z-10" />
        )}
        {(weather === "Chuvoso" || weather === "Tempestade") && (
          <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden bg-blue-900/5">
            <div className="rain-effect opacity-35" />
          </div>
        )}
        {weather === "Nevoeiro" && (
          <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden bg-slate-800/15">
            {/* soft mist layers (see .fog-effect) — not tiled dots */}
            <div className="fog-effect" />
          </div>
        )}

        {/* Banner de Intro Dramática do Inimigo/Boss */}
        {(() => {
          const introEffect = effects.find(e => e.type === 'enemy_intro');
          if (!introEffect) return null;
          return (
            <div className="absolute inset-0 bg-black/85 flex items-center justify-center z-50 animate-fade-in pointer-events-none">
              <div className={`w-full py-8 text-center border-y backdrop-blur-sm shadow-[0_0_50px_rgba(0,0,0,0.8)] transition-all duration-300
                              ${introEffect.color === 'shadow_purple'
                                ? 'bg-purple-950/85 border-purple-800/80 text-purple-400 shadow-purple-900/30'
                                : 'bg-red-950/85 border-red-800/80 text-red-400 shadow-red-900/30'}`}>
                <div className="font-cinzel text-xs tracking-[0.3em] font-black uppercase text-gray-400 animate-pulse mb-1">
                  ⚠️ INIMIGO DESAFIANTE ⚠️
                </div>
                <h1 className="font-cinzel font-black text-2xl md:text-4xl tracking-widest uppercase drop-shadow-[0_0_15px_rgba(0,0,0,0.9)]">
                  {introEffect.text}
                </h1>
              </div>
            </div>
          );
        })()}

        {/* Overlay do CombatMoment (Rendição/Diálogo de Boss) */}
        {uiContext?.type === 'COMBAT_MOMENT' && (
          <div className="absolute inset-0 bg-black/90 flex flex-col items-center justify-center p-6 text-center z-40 animate-fade-in">
            <div className="max-w-2xl border border-red-900/60 bg-gray-950/95 p-6 rounded-lg shadow-[0_0_50px_rgba(0,0,0,0.95)] backdrop-blur-md">
              <h2 className="text-red-500 font-cinzel font-black tracking-widest text-lg md:text-xl mb-4 uppercase animate-pulse">
                ⚠️ MOMENTO DECISIVO ⚠️
              </h2>
              <p className="text-gray-300 font-inter text-sm md:text-base leading-relaxed whitespace-pre-line">
                {uiContext.prompt}
              </p>
            </div>
          </div>
        )}

        {/* Background atmosférico usando cenário atual */}
        {gameState?.current_location && (
          <div
            className="absolute inset-0 bg-cover bg-center opacity-15"
            style={{ backgroundImage: `url('/cenario_${gameState.current_location}.jpg')`,
                     filter: 'blur(2px)' }}
          />
        )}

        {/* Vignette nas bordas */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_50%,transparent_40%,rgba(0,0,0,0.85)_100%)] pointer-events-none z-10" />

        {/* Linha de chão */}
        <div className="absolute bottom-16 left-0 right-0 h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent opacity-40 z-10" />

        {/* Scanlines */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:100%_4px] pointer-events-none z-10" />

        {/* Projectile animations layer */}
        <ProjectileLayer />

        {/* Global screen flashes (damage / crit / heal / lightning) */}
        {effects
          .filter((e) => e.type === 'screen_flash' || e.type === 'lightning')
          .map((e) => (
            <div
              key={e.id}
              className={`screen-flash ${
                e.type === 'lightning' ? 'lightning' : e.color || 'damage'
              }`}
            />
          ))}

        {/* Herói (Esquerda) */}
        <div className="flex flex-col gap-4 z-20 shrink-0 items-center justify-center min-h-[300px]">
            {(gameState?.party || [gameState?.player]).map((member: any) => {
                if (!member) return null;
                const memberClientId = member.client_id || 'leader';
                const partyTid = `party_${memberClientId}`;
                const hasSubmitted = combatState?.submitted_actions?.includes(memberClientId);
                const isMe = memberClientId === myClientId || (!myClientId && memberClientId === 'leader');
                const memberClass = member.char_class || member.class;
                const hasShake = effects.some(e => (e.targetId === partyTid || e.targetId === memberClientId) && e.type === 'shake');
                const hasImpact = effects.some(e => (e.targetId === partyTid || e.targetId === memberClientId) && e.type === 'impact');
                const hasHealGlow = effects.some(e => e.type === 'heal_glow' && (e.targetId === memberClientId || e.targetId === partyTid || e.targetId === 'leader'));
                const auraClass = getSubclassAuraClass(member.talents_unlocked);
                const numbers = effects.filter(
                  e => (e.type === 'damage_number' || e.type === 'heal_number') &&
                    (e.targetId === partyTid || e.targetId === memberClientId)
                );
                return (
                    <div key={memberClientId}
                         className={`relative flex flex-col items-center w-32 transition-all duration-500 rounded-lg p-1.5
                                    ${hasSubmitted ? 'opacity-40 grayscale' : 'opacity-100'}
                                    ${isMe ? 'ring-2 ring-yellow-400 bg-yellow-950/15' : ''}
                                    ${auraClass}
                                    ${hasShake ? 'animate-shake' : ''}
                                    ${hasHealGlow ? 'animate-heal-glow' : ''}`}>
                        {hasImpact && (
                          <div className={`impact-ring ${effects.some(e => e.targetId === partyTid && e.isCrit) ? 'crit' : ''}`} />
                        )}
                        {numbers.map((n) => (
                          <span
                            key={n.id}
                            className={`floating-number ${n.type === 'heal_number' ? 'heal' : 'dmg'} ${n.isCrit ? 'crit' : ''}`}
                            style={{ ['--dx' as any]: `${(Math.random() * 24 - 12).toFixed(0)}px` }}
                          >
                            {n.text}
                          </span>
                        ))}
                        <div className="w-full h-2 bg-gray-900 rounded-full overflow-hidden mb-0.5">
                            <div className="h-full bg-gradient-to-r from-red-700 to-red-500 transition-all duration-500"
                                 style={{ width: `${(member.hp / member.max_hp) * 100}%` }} />
                        </div>
                        <div className="w-full h-1.5 bg-gray-900 rounded-full overflow-hidden mb-1">
                            <div className="h-full bg-gradient-to-r from-blue-700 to-blue-500 transition-all duration-500"
                                 style={{ width: `${(member.mp / (member.max_mp || 1)) * 100}%` }} />
                        </div>
                        <img src={getHeroSprite(memberClass)}
                             className={`w-24 h-24 object-contain drop-shadow-[0_0_10px_rgba(255,255,255,0.05)] ${hasImpact ? 'animate-hit-flash' : ''}`}
                             alt={member.name} />
                        <div className="mt-1 text-xs font-cinzel font-bold text-center"
                             style={{ color: isMe ? '#fbbf24' : '#9ca3af' }}>
                            {member.name}
                            {hasSubmitted && <span className="block text-green-400 text-[10px]">✅ Pronto</span>}
                            {!hasSubmitted && <span className="block text-yellow-400 text-[10px] animate-pulse">⚔️ Decidindo...</span>}
                        </div>
                    </div>
                );
            })}
        </div>

        {/* Floating text effects (e.g. Level Up) */}
        {effects.map((e) => {
          if (e.type === 'text' && e.targetId === 'player') {
            return (
              <div
                key={e.id}
                className="absolute inset-0 flex items-center justify-center pointer-events-none z-50 animate-bounce"
              >
                <div
                  className="text-4xl md:text-6xl font-cinzel font-black tracking-widest text-center"
                  style={{
                    color: e.color || 'gold',
                    textShadow: '0 0 20px rgba(243,156,18,0.8), 0 0 40px rgba(243,156,18,0.4)',
                  }}
                >
                  {e.text}
                </div>
              </div>
            );
          }
          return null;
        })}

        {/* Inimigos (Direita) */}
        <div className="flex flex-row gap-6 z-20 shrink-0 items-end">
          {combatState.enemies.map((enemy: Enemy) => {
            const tid = `enemy_${enemy.idx}`;
            const hasShake = effects.some(e => e.targetId === tid && e.type === 'shake');
            const hasImpact = effects.some(e => e.targetId === tid && e.type === 'impact');
            const hasHealGlow = effects.some(e => e.type === 'heal_glow' && e.targetId === tid);
            const hasCritBurst = effects.some(e => e.targetId === tid && e.type === 'crit_burst');
            const numbers = effects.filter(
              e => (e.type === 'damage_number' || e.type === 'heal_number') && e.targetId === tid
            );
            return (
              <div
                key={enemy.idx}
                className={`relative flex flex-col items-center w-64 transition-all duration-700 ${
                  !enemy.alive ? 'animate-death' : ''
                } ${hasShake ? 'animate-shake' : ''} ${hasHealGlow ? 'animate-heal-glow' : ''}`}
              >
                {hasImpact && (
                  <div className={`impact-ring ${effects.some(e => e.targetId === tid && e.isCrit) ? 'crit' : ''}`} />
                )}
                {hasCritBurst && (
                  <div className="particle-burst" style={{ color: '#ffb347' }}>
                    {Array.from({ length: 10 }).map((_, i) => {
                      const ang = (i / 10) * Math.PI * 2;
                      const dist = 48 + (i % 3) * 12;
                      return (
                        <span
                          key={i}
                          style={{
                            ['--px' as any]: `${Math.cos(ang) * dist}px`,
                            ['--py' as any]: `${Math.sin(ang) * dist}px`,
                            animationDelay: `${i * 12}ms`,
                          }}
                        />
                      );
                    })}
                  </div>
                )}
                {numbers.map((n) => (
                  <span
                    key={n.id}
                    className={`floating-number ${n.type === 'heal_number' ? 'heal' : 'dmg'} ${n.isCrit ? 'crit' : ''}`}
                    style={{ ['--dx' as any]: `${(Math.random() * 28 - 14).toFixed(0)}px` }}
                  >
                    {n.text}
                  </span>
                ))}
                {/* Barra HP inimigo */}
                <div className="w-full mb-2 relative">
                  <div className="w-full h-4 bg-gray-900/80 rounded-full overflow-hidden border border-gray-700">
                    <div
                      className="h-full bg-gradient-to-r from-red-800 to-red-500 transition-all duration-300 shadow-[0_0_10px_rgba(220,38,38,0.5)]"
                      style={{ width: `${(enemy.hp / enemy.max_hp) * 100}%` }}
                    />
                  </div>
                  {enemy.hp > 0 && (
                    <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold font-mono text-white">
                      {enemy.hp}/{enemy.max_hp}
                    </span>
                  )}
                </div>

                {/* Barra MP inimigo */}
                {enemy.max_mp > 0 && (
                  <div className="w-full mb-2">
                    <div className="w-full h-1.5 bg-gray-900/80 rounded-full overflow-hidden border border-gray-700">
                      <div
                        className="h-full bg-gradient-to-r from-blue-800 to-blue-500 transition-all duration-300"
                        style={{ width: `${(enemy.mp / enemy.max_mp) * 100}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Sprite ou Emoji fallback */}
                {(() => {
                  const sprite = getEnemySprite(enemy.name);
                  if (sprite) {
                    return (
                      <img
                        src={sprite}
                        alt={enemy.name}
                        className={`w-56 h-56 object-contain ${enemy.alive ? 'drop-shadow-[0_0_25px_rgba(220,38,38,0.4)]' : ''} ${hasImpact ? 'animate-hit-flash' : ''}`}
                      />
                    );
                  }
                  return (
                    <div className={`w-56 h-56 flex items-center justify-center text-7xl rounded bg-gradient-to-br from-gray-900 to-black border border-gray-800 ${enemy.alive ? 'shadow-[0_0_30px_rgba(220,38,38,0.2)]' : ''} ${hasImpact ? 'animate-hit-flash' : ''}`}>
                      {getEnemyFallbackEmoji(enemy.name)}
                    </div>
                  );
                })()}

                <div className="mt-3 font-cinzel font-bold text-red-400 text-sm bg-gray-950/90 px-3 py-1 rounded border border-red-900/50 text-center">
                  {enemy.name}
                </div>

                {enemy.intent && enemy.alive && (
                  <span
                    className={`mt-1 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded border ${
                      INTENT_STYLE[enemy.intent.category] || INTENT_STYLE.none
                    }`}
                    title={
                      enemy.intent.uninterruptible
                        ? 'Ação ininterrupível'
                        : enemy.intent.interrupted
                          ? 'Interrompido'
                          : `Intenção: ${enemy.intent.label}`
                    }
                  >
                    {INTENT_ICON[enemy.intent.category] || '·'}{' '}
                    {enemy.intent.interrupted
                      ? 'Interrompido'
                      : enemy.intent.label}
                    {enemy.intent.uninterruptible && !enemy.intent.interrupted
                      ? ' ⛔'
                      : ''}
                  </span>
                )}

                {enemy.defending && (
                  <span className="text-xs text-blue-400 mt-1 font-bold animate-pulse">
                    🛡️ DEFENDENDO
                  </span>
                )}
                {enemy.status?.map(st => (
                  <span key={st} className="mt-1 px-2 py-0.5 text-[10px] font-bold bg-purple-900/50 text-purple-300 rounded border border-purple-700/50 animate-pulse">
                    {st}
                  </span>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Painel de Comandos (Rodapé) */}
      <div className="h-40 md:h-48 bg-gray-950 border-t border-red-900/30 p-4 md:p-6 flex flex-col justify-center shadow-[inset_0_20px_40px_rgba(0,0,0,0.8)] z-20">
        {combatState?.phase === 'WAITING_ALL_PLAYERS' && combatState?.submitted_actions?.includes(myClientId) ? (
          <div className="flex items-center justify-center h-full w-full">
            <div className="text-emerald-400 animate-pulse font-bold text-lg md:text-xl tracking-widest uppercase flex items-center gap-2">
              <span className="inline-block animate-spin text-xl">⏳</span> ✅ Ação enviada! Aguardando os outros jogadores...
            </div>
          </div>
        ) : !isLeader && combatState?.phase !== 'WAITING_ALL_PLAYERS' && (uiContext?.options || uiContext?.subtype === 'PRESS_ANY_KEY') ? (
          <div className="text-gray-500 text-center py-8 italic flex items-center justify-center gap-2">
            ⚔️ Aguardando decisão do líder da party...
          </div>
        ) : uiContext?.subtype === 'PRESS_ANY_KEY' ? (
          <div className="flex items-center justify-center h-full w-full">
            <button
              onClick={() => sendAction({ action: "INPUT", value: " " })}
              className="w-full py-6 bg-gray-900 hover:bg-gray-800 border border-gray-700 hover:border-red-500 rounded text-red-500 font-bold text-lg tracking-widest transition-all hover:shadow-[0_0_20px_rgba(220,38,38,0.3)]"
            >
              ▶ Pressionar para continuar
            </button>
          </div>
        ) : uiContext?.options ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 w-full h-full items-center">
            {Object.entries(uiContext.options).map(([key, value]) => (
              <button
                key={key}
                onClick={() => handleOptionClick(key)}
                className={`group relative overflow-hidden bg-gray-900/50 border rounded transition-all duration-200 py-4 px-4 text-left h-auto whitespace-normal font-inter text-sm ${getActionStyle(key, String(value))}`}
              >
                <span className="text-gray-600 mr-2 text-xs font-mono">[{key}]</span>
                <span className="tracking-wide">{String(value)}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-red-400 animate-pulse font-bold text-xl tracking-widest uppercase mb-1">
              {combatState?.phase === 'ENEMY_TURN' ? `⚔️ Inimigo está agindo...` :
               combatState?.phase === 'PARTY_EXECUTE' ? `⚔️ Personagens atacando...` :
               combatState?.phase === 'COMPANION_TURN' ? `🤝 Companheiro está agindo...` :
               combatState?.phase === 'TURN_START' ? `⏳ Início do turno...` :
               uiContext?.prompt || "Aguardando Turno..."}
            </div>
            {combatState.logs && combatState.logs.length > 0 && (
              <div className="text-gray-500 font-mono text-xs text-center line-clamp-1 italic max-w-lg">
                {combatState.logs[combatState.logs.length - 1]}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
