import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { audioManager } from '../audio/AudioManager';

// Define shapes of the game state as expected from the server
export interface GameState {
  session_id: string;
  created_at: string;
  current_chapter: number;
  current_location: string;
  flags: Record<string, any>;
  player: {
    name: string;
    level: number;
    hp: number;
    max_hp: number;
    mp: number;
    max_mp: number;
    gold: number;
    class: number; // or string based on enum
    xp?: number;
    xp_next_level?: number;
    companion?: {
      name: string;
      description: string;
      hp: number;
      max_hp: number;
    } | null;
  };
  in_combat: boolean;
  combat_state?: any; // To be refined in CombatView
  party?: Array<{
    client_id?: string | null;
    name: string;
    level: number;
    hp: number;
    max_hp: number;
    mp: number;
    max_mp: number;
    gold: number;
    char_class?: string | number;
    class?: number | string;
  }>;
}

// Additional UI context that might come from the server
export interface UIContext {
  prompt: string;
  options?: Record<string, string>;
  message?: string;
  type: string; // "WAITING_INPUT", "STATE_UPDATE", "GAME_OVER", "ERROR"
  subtype?: string;
}

interface WebSocketContextProps {
  gameState: GameState | null;
  uiContext: UIContext | null;
  narrativeLog: string[];
  clearNarrative: () => void;
  connected: boolean;
  sendAction: (actionPayload: object) => void;
  error: string | null;
  lobbyState: any | null;      // Holds lobby info
  gameStarted: boolean;        // true when GAME_START is received
  isLeader: boolean;
  myClientId: string | null;
  systemNotification: string | null;
  setSystemNotification: (val: string | null) => void;
}

const WebSocketContext = createContext<WebSocketContextProps>({
  gameState: null,
  uiContext: null,
  narrativeLog: [],
  clearNarrative: () => {},
  connected: false,
  sendAction: () => {},
  error: null,
  lobbyState: null,
  gameStarted: false,
  isLeader: false,
  myClientId: null,
  systemNotification: null,
  setSystemNotification: () => {},
});

export const useGame = () => useContext(WebSocketContext);

interface ProviderProps {
  children: React.ReactNode;
  sessionId: string;
  playerName?: string;
  playerClass?: string;
}

import { useVisualEffects } from './VisualEffectProvider';

export const WebSocketProvider: React.FC<ProviderProps> = ({ children, sessionId, playerName, playerClass }) => {
  const { triggerEffect } = useVisualEffects();
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [uiContext, setUiContext] = useState<UIContext | null>(null);
  const [narrativeLog, setNarrativeLog] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lobbyState, setLobbyState] = useState<any | null>(null);
  const [gameStarted, setGameStarted] = useState<boolean>(false);
  const [isLeader, setIsLeader] = useState<boolean>(false);
  const [myClientId, setMyClientId] = useState<string | null>(null);
  const [systemNotification, setSystemNotification] = useState<string | null>(null);

  useEffect(() => {
    if (systemNotification) {
      const timer = setTimeout(() => {
        setSystemNotification(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [systemNotification]);

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<any>(null);

  const connect = useCallback(() => {
    if (!sessionId) return;
    
    const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const WS_URL = `${wsScheme}://${window.location.host}`;
    
    const queryParams = new URLSearchParams();
    if (playerName) queryParams.append('name', playerName);
    if (playerClass) queryParams.append('class', playerClass);
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';

    ws.current = new WebSocket(`${WS_URL}/ws/${sessionId}${queryString}`);

    ws.current.onopen = () => {
      setConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        let currentMyId = myClientId;
        if (data.my_client_id) {
          setMyClientId(data.my_client_id);
          currentMyId = data.my_client_id;
        }
        
        const leaderId = data.leader_client_id || data.leader_id || (data.type === 'LOBBY_UPDATE' ? data.leader_id : null);
        let checkIsLeader = isLeader;
        if (currentMyId && leaderId) {
          const isL = leaderId === currentMyId;
          setIsLeader(isL);
          checkIsLeader = isL;
        }
        
        if (data.type === 'LOBBY_UPDATE') {
          setLobbyState(data);
        } else if (data.type === 'GAME_START') {
          setGameStarted(true);
        } else if (data.type === 'STATE_UPDATE' && data.state) {
          const combatPhase = data.state.combat_state?.phase;
          const combatEnded = !data.state.in_combat;
          if (combatEnded) {
            setUiContext(null);
          } else if (checkIsLeader || data.state.in_combat) {
            if (combatPhase !== 'WAITING_ALL_PLAYERS') {
              setUiContext(prev => (prev && prev.type === 'COMBAT_MOMENT') ? prev : null);
            }
          }
          setGameState(prev => {
            if (prev && prev.current_chapter !== data.state.current_chapter) {
              setNarrativeLog([]);
            }
            if (prev && prev.in_combat && !data.state.in_combat) {
              setUiContext(null);
            }
            return data.state;
          });
          try {
            const state = data.state;
            const chapter = state.flags?.lacre_sombrio ? 3 : (state.flags?.cavernas_iniciada ? 2 : 1);
            localStorage.setItem('pika_save', JSON.stringify({
              session_id: sessionId,
              player_name: state.player?.name || "Herói",
              chapter: chapter,
              location: state.current_location || "Mundo",
              saved_at: new Date().toISOString()
            }));
          } catch (e) {
            console.error('Failed to save metadata to localStorage', e);
          }
        } else if (data.type === 'NARRATIVE_TEXT') {
          const isSystemMessage = (text: string) => 
              text.startsWith("✅") && text.includes("está pronto");
          if (!isSystemMessage(data.content)) {
            setNarrativeLog(prev => [...prev, data.content]);
          } else {
            setSystemNotification(data.content);
          }
        } else if (data.type === 'SOUND_EFFECT') {
          audioManager.playSFX(data.effect_id);
        } else if (data.type === 'WAITING_INPUT') {
          // Keep previous game state, just update the UI waiting state
          setUiContext({
            type: data.type,
            prompt: data.prompt,
            options: data.options,
            subtype: data.subtype,
          });
        } else if (data.type === 'COMBAT_MOMENT') {
          setUiContext({
            type: data.type,
            prompt: data.text,
            options: data.options,
          });
        } else if (data.type === 'GAME_OVER' || data.type === 'ERROR') {
          setUiContext({
            type: data.type,
            prompt: data.message || "",
          });
        } else if (data.type === 'VISUAL_EFFECT') {
          triggerEffect({
            type: data.effect_type,
            targetId: data.target_id || 'global',
            text: data.text,
            color: data.color,
            duration: data.duration || 2500,
            fromSide: data.from_side,
            projectileStyle: data.style,
          });
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    ws.current.onerror = () => {
      setError('WebSocket connection error.');
    };

    ws.current.onclose = () => {
      setConnected(false);
      const attempts = reconnectAttempts.current;
      if (attempts < 5) {
        const delay = Math.min(1000 * Math.pow(2, attempts), 30000);
        reconnectAttempts.current += 1;
        reconnectTimeout.current = setTimeout(connect, delay);
      } else {
        setError('Conexão perdida. Recarregue a página.');
      }
    };
  }, [sessionId, playerName, playerClass]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  const clearNarrative = () => setNarrativeLog([]);

  const sendAction = (actionPayload: object) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(actionPayload));
      // Clear UI context immediately so we don't send duplicate commands while waiting
      setUiContext(null); 
    }
  };

  return (
    <WebSocketContext.Provider value={{ gameState, uiContext, narrativeLog, clearNarrative, connected, sendAction, error, lobbyState, gameStarted, isLeader, myClientId, systemNotification, setSystemNotification }}>
      {children}
    </WebSocketContext.Provider>
  );
};
