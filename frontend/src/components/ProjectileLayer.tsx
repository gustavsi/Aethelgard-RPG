import React from 'react';
import { useVisualEffects } from '../contexts/VisualEffectProvider';

const PROJECTILE_ICON: Record<string, string> = {
    fireball: '🔥',
    arrow: '➤',
    slash: '💥',
    holy_bolt: '✨',
};

export const ProjectileLayer: React.FC = () => {
    const { effects } = useVisualEffects();
    const projectiles = effects.filter((e: any) => e.type === 'projectile');

    return (
        <div className="absolute inset-0 pointer-events-none z-30 overflow-hidden">
            {projectiles.map((p: any) => (
                <div
                    key={p.id}
                    className={`projectile-icon ${
                        p.fromSide === 'party' ? 'animate-projectile-right' : 'animate-projectile-left'
                    }`}
                    style={{ animationDuration: `${p.duration}ms` }}
                >
                    {PROJECTILE_ICON[p.projectileStyle] || '⚡'}
                </div>
            ))}
        </div>
    );
};
