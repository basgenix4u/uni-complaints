import React from 'react';
import { cn } from '../../utils/cn';

const badgeVariants = {
  primary: 'badge-primary',
  secondary: 'badge-secondary',
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
  info: 'badge-info',
};

const Badge = ({
  children,
  variant = 'primary',
  className = '',
  dot = false,
  ...props
}) => {
  return (
    <span className={cn('badge', badgeVariants[variant], className)} {...props}>
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            variant === 'success' && 'bg-success-500',
            variant === 'warning' && 'bg-warning-500',
            variant === 'danger' && 'bg-danger-500',
            variant === 'info' && 'bg-info-500',
            variant === 'primary' && 'bg-primary-500',
            variant === 'secondary' && 'bg-neutral-500'
          )}
        />
      )}
      {children}
    </span>
  );
};

export default Badge;