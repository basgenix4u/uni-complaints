import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { formatNumber } from '../../utils/helpers';

const iconBgColors = {
  primary: 'bg-primary-100 text-primary-600',
  secondary: 'bg-neutral-100 text-neutral-600',
  success: 'bg-success-100 text-success-600',
  warning: 'bg-warning-100 text-warning-600',
  danger: 'bg-danger-100 text-danger-600',
  info: 'bg-info-100 text-info-600',
};

const StatCard = ({
  title,
  value,
  icon: Icon,
  change,
  changeType = 'neutral',
  color = 'primary',
  delay = 0,
  className = '',
}) => {
  const changeColors = {
    increase: 'text-success-600 bg-success-50',
    decrease: 'text-danger-600 bg-danger-50',
    neutral: 'text-neutral-600 bg-neutral-50',
  };

  const changeIcons = {
    increase: '↑',
    decrease: '↓',
    neutral: '→',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.1, 0.25, 1] }}
      className={cn(
        'bg-white rounded-2xl shadow-soft border border-neutral-100 p-6 hover:shadow-soft-xl transition-shadow',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-neutral-500 mb-1">{title}</p>
          <motion.p
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: delay + 0.2, type: 'spring', stiffness: 200 }}
            className="text-3xl font-bold text-neutral-900"
          >
            {typeof value === 'number' ? formatNumber(value) : value}
          </motion.p>

          {change !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              <span
                className={cn(
                  'inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-medium',
                  changeColors[changeType]
                )}
              >
                <span>{changeIcons[changeType]}</span>
                {change}
              </span>
              <span className="text-xs text-neutral-400">vs last period</span>
            </div>
          )}
        </div>

        {Icon && (
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: delay + 0.1, type: 'spring', stiffness: 200 }}
            className={cn(
              'w-12 h-12 rounded-xl flex items-center justify-center',
              iconBgColors[color]
            )}
          >
            <Icon className="w-6 h-6" />
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

export default StatCard;