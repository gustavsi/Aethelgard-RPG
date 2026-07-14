import React, { createContext, useContext, useState, useCallback } from 'react';

export type VfxType =
  | 'shake'
  | 'flash'
  | 'particles'
  | 'text'
  | 'enemy_intro'
  | 'projectile'
  | 'heal_glow'
  | 'impact'
  | 'damage_number'
  | 'heal_number'
  | 'screen_flash'
  | 'lightning'
  | 'crit_burst';

export interface VisualEffect {
  id: string;
  type: VfxType;
  targetId: string;
  color?: string;
  duration: number;
  text?: string;
  fromSide?: 'party' | 'enemy';
  projectileStyle?: 'fireball' | 'arrow' | 'slash' | 'holy_bolt' | string;
  amount?: number;
  isCrit?: boolean;
}

interface VisualEffectContextProps {
  effects: VisualEffect[];
  triggerEffect: (effect: Omit<VisualEffect, 'id'>) => void;
  removeEffect: (id: string) => void;
}

const VisualEffectContext = createContext<VisualEffectContextProps | undefined>(undefined);

export const VisualEffectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [effects, setEffects] = useState<VisualEffect[]>([]);

  const triggerEffect = useCallback((effect: Omit<VisualEffect, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newEffect = { ...effect, id };
    setEffects((prev) => [...prev, newEffect]);

    const duration = Math.max(100, effect.duration || 800);
    setTimeout(() => {
      setEffects((prev) => prev.filter((e) => e.id !== id));
    }, duration);
  }, []);

  const removeEffect = useCallback((id: string) => {
    setEffects((prev) => prev.filter((e) => e.id !== id));
  }, []);

  return (
    <VisualEffectContext.Provider value={{ effects, triggerEffect, removeEffect }}>
      {children}
    </VisualEffectContext.Provider>
  );
};

export const useVisualEffects = () => {
  const context = useContext(VisualEffectContext);
  if (!context) {
    throw new Error('useVisualEffects must be used within a VisualEffectProvider');
  }
  return context;
};
