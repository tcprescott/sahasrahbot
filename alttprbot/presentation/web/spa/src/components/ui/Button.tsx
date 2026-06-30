import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'ghost';

interface CommonProps {
  variant?: Variant;
  small?: boolean;
  children: ReactNode;
  className?: string;
}

function classes({ variant = 'primary', small, className }: CommonProps): string {
  return [
    'btn',
    variant === 'primary' ? 'btn-primary' : 'btn-ghost',
    small ? 'btn-sm' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');
}

type ButtonProps = CommonProps & ButtonHTMLAttributes<HTMLButtonElement>;
type LinkProps = CommonProps & { href: string } & AnchorHTMLAttributes<HTMLAnchorElement>;

export function Button({ variant, small, className, children, ...rest }: ButtonProps) {
  return (
    <button className={classes({ variant, small, className, children })} {...rest}>
      {children}
    </button>
  );
}

export function ButtonLink({ variant, small, className, children, ...rest }: LinkProps) {
  return (
    <a className={classes({ variant, small, className, children })} {...rest}>
      {children}
    </a>
  );
}
