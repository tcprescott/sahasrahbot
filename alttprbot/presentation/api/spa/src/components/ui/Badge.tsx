import type { ReactNode } from 'react';

type Tone = 'default' | 'gold' | 'teal' | 'violet' | 'crimson';

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  /** show a leading status dot */
  dot?: boolean;
  className?: string;
}

export function Badge({ children, tone = 'default', dot, className }: BadgeProps) {
  const cls = ['badge', tone !== 'default' ? tone : '', className ?? ''].filter(Boolean).join(' ');
  return (
    <span className={cls}>
      {dot && <span className="dot" />}
      {children}
    </span>
  );
}
