import React from 'react';
import { cn } from '../../utils/cn';

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-6 h-6 border-2',
  lg: 'w-8 h-8 border-3',
  xl: 'w-12 h-12 border-4',
};

const Spinner = ({ size = 'md', className = '', color = 'primary' }) => {
  const colorClasses = {
    primary: 'border-primary-500',
    white: 'border-white',
    neutral: 'border-neutral-500',
  };

  return (
    <div
      className={cn(
        'rounded-full border-t-transparent animate-spin',
        sizeClasses[size],
        colorClasses[color],
        className
      )}
    />
  );
};

export default Spinner;