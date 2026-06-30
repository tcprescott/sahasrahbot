import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return <div className={['panel', className ?? ''].filter(Boolean).join(' ')}>{children}</div>;
}

export function CardHead({ children, className }: CardProps) {
  return <div className={['panel-head', className ?? ''].filter(Boolean).join(' ')}>{children}</div>;
}

export function CardBody({ children, className }: CardProps) {
  return <div className={['panel-body', className ?? ''].filter(Boolean).join(' ')}>{children}</div>;
}
