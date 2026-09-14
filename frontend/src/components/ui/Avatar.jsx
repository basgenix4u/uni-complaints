import React from 'react';
import { cn } from '../../utils/cn';
import { getInitials, stringToColor } from '../../utils/helpers';

const sizeClasses = {
  xs: 'w-6 h-6 text-2xs',
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
  xl: 'w-16 h-16 text-lg',
  '2xl': 'w-20 h-20 text-xl',
};

const Avatar = ({
  name,
  src,
  size = 'md',
  className = '',
  showStatus = false,
  status = 'online',
  ...props
}) => {
  const initials = getInitials(name);
  const bgColor = stringToColor(name);

  const statusColors = {
    online: 'bg-success-500',
    offline: 'bg-neutral-400',
    busy: 'bg-danger-500',
    away: 'bg-warning-500',
  };

  return (
    <div className={cn('relative inline-flex', className)} {...props}>
      {src ? (
        <img
          src={src}
          alt={name}
          className={cn(
            'rounded-full object-cover ring-2 ring-white shadow-lg',
            sizeClasses[size]
          )}
        />
      ) : (
        <div
          className={cn(
            'rounded-full flex items-center justify-center font-semibold text-white ring-2 ring-white shadow-lg',
            bgColor,
            sizeClasses[size]
          )}
        >
          {initials}
        </div>
      )}

      {showStatus && (
        <span
          className={cn(
            'absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full ring-2 ring-white',
            statusColors[status]
          )}
        />
      )}
    </div>
  );
};

export default Avatar;