import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '../../utils/cn';

const Textarea = React.forwardRef(
  (
    {
      label,
      error,
      hint,
      className = '',
      containerClassName = '',
      required = false,
      disabled = false,
      rows = 4,
      ...props
    },
    ref
  ) => {
    return (
      <div className={cn('w-full', containerClassName)}>
        {label && (
          <label className="label">
            {label}
            {required && <span className="text-danger-500 ml-1">*</span>}
          </label>
        )}

        <textarea
          ref={ref}
          rows={rows}
          disabled={disabled}
          className={cn(
            'textarea',
            error && 'input-error',
            disabled && 'cursor-not-allowed opacity-60',
            className
          )}
          {...props}
        />

        <AnimatePresence>
          {error && (
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-1.5 text-sm text-danger-600 flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              {error}
            </motion.p>
          )}
        </AnimatePresence>

        {hint && !error && (
          <p className="mt-1.5 text-sm text-neutral-500">{hint}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export default Textarea;