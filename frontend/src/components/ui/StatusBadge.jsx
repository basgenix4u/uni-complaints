import React from 'react';
import { cn } from '../../utils/cn';
import { getStatusConfig, getPriorityConfig } from '../../utils/helpers';

export const StatusBadge = ({ status, className = '' }) => {
  const config = getStatusConfig(status);
  
  return (
    <span className={cn(config.badgeClass, className)}>
      {config.label}
    </span>
  );
};

export const PriorityBadge = ({ priority, className = '' }) => {
  const config = getPriorityConfig(priority);
  
  return (
    <span className={cn(config.badgeClass, className)}>
      {config.label}
    </span>
  );
};