import React from 'react';
import { useVisualEffects } from '../contexts/VisualEffectProvider';

const STYLE_CLASS: Record<string, string> = {
  fireball: 'proj-fireball',
  arrow: 'proj-arrow',
  slash: 'proj-slash',
  holy_bolt: 'proj-holy',
};

/** Stylized CSS projectiles with trail — replaces emoji "💩" combat FX. */
export const ProjectileLayer: React.FC = () => {
  const { effects } = useVisualEffects();
  const projectiles = effects.filter((e) => e.type === 'projectile');

  return (
    <div className="absolute inset-0 pointer-events-none z-30 overflow-hidden">
      {projectiles.map((p) => {
        const styleKey = p.projectileStyle || 'slash';
        const styleClass = STYLE_CLASS[styleKey] || 'proj-default';
        const dirClass =
          p.fromSide === 'party' ? 'animate-projectile-right' : 'animate-projectile-left';
        return (
          <div
            key={p.id}
            className={`projectile-core ${styleClass} ${dirClass}`}
            style={{ animationDuration: `${p.duration || 600}ms` }}
          >
            <span className="projectile-trail" />
            <span className="projectile-core-inner" />
            <span className="projectile-spark s1" />
            <span className="projectile-spark s2" />
          </div>
        );
      })}
    </div>
  );
};
