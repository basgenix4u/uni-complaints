import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { cn } from '../../utils/cn';

const Input = React.forwardRef(
  (
    {
      label,
      error,
      hint,
      leftIcon,
      rightIcon,
      type = 'text',
      className = '',
      containerClassName = '',
      required = false,
      disabled = false,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = useState(false);

    const isPassword = type === 'password';
    const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

    return (
      <div className={cn('w-full', containerClassName)}>
        {label && (
          <label className="label">
            {label}
            {required && <span className="text-danger-500 ml-1">*</span>}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            type={inputType}
            disabled={disabled}
            className={cn(
              'input',
              error && 'input-error',
              leftIcon && 'pl-11',
              (rightIcon || isPassword) && 'pr-11',
              disabled && 'cursor-not-allowed opacity-60',
              className
            )}
            {...props}
          />

          {isPassword && (
            <button
              type="button"
              className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 
                         hover:text-neutral-600 transition-colors"
              onClick={() => setShowPassword(!showPassword)}
              tabIndex={-1}
            >
              {showPassword ? (
                <EyeSlashIcon className="w-5 h-5" />
              ) : (
                <EyeIcon className="w-5 h-5" />
              )}
            </button>
          )}

          {rightIcon && !isPassword && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400">
              {rightIcon}
            </div>
          )}
        </div>

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

Input.displayName = 'Input';

export default Input;