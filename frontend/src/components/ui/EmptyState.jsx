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
      className={`flex flex-col items-center justify-center py-10 text-center sm:py-16 ${className}`}
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
        className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-100 sm:mb-4 sm:h-20 sm:w-20"
      >
        <IconComponent className="h-8 w-8 text-neutral-400 sm:h-10 sm:w-10" />
      </motion.div>

      <motion.h3
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="mb-2 text-lg font-semibold text-neutral-900 sm:text-xl"
      >
        {title}
      </motion.h3>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mb-5 max-w-sm text-sm text-neutral-500 sm:mb-6 sm:text-base"
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