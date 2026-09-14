import React from 'react';
import { motion } from 'framer-motion';
import { InboxIcon } from '@heroicons/react/24/outline';
import Button from './Button';

const EmptyState = ({
  icon: IconComponent = InboxIcon,
  title = 'No data found',
  description = 'There are no items to display.',
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex flex-col items-center justify-center py-16 text-center ${className}`}
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
        className="w-20 h-20 rounded-full bg-neutral-100 flex items-center justify-center mb-4"
      >
        <IconComponent className="w-10 h-10 text-neutral-400" />
      </motion.div>

      <motion.h3
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-xl font-semibold text-neutral-900 mb-2"
      >
        {title}
      </motion.h3>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="text-neutral-500 max-w-sm mb-6"
      >
        {description}
      </motion.p>

      {actionLabel && onAction && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Button onClick={onAction}>{actionLabel}</Button>
        </motion.div>
      )}
    </motion.div>
  );
};

export default EmptyState;