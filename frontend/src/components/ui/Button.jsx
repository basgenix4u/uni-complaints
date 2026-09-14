import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

const buttonVariants = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  success: 'btn-success',
  danger: 'btn-danger',
  warning: 'btn-warning',
  outline: 'btn-outline',
  'outline-primary': 'btn-outline-primary',
  ghost: 'btn-ghost',
  link: 'btn-link',
};

const buttonSizes = {
  sm: 'btn-sm',
  md: 'btn-md',
  lg: 'btn-lg',
  xl: 'btn-xl',
  icon: 'p-2.5',
};

const Button = React.forwardRef(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      className = '',
      disabled = false,
      loading = false,
      leftIcon = null,
      rightIcon = null,
      fullWidth = false,
      type = 'button',
      animate = true,
      ...props
    },
    ref
  ) => {
    const Comp = animate ? motion.button : 'button';

    const animationProps = animate
      ? {
          whileHover: { scale: disabled || loading ? 1 : 1.02 },
          whileTap: { scale: disabled || loading ? 1 : 0.98 },
          transition: { type: 'spring', stiffness: 400, damping: 17 },
        }
      : {};

    return (
      <Comp
        ref={ref}
        type={type}
        disabled={disabled || loading}
        className={cn(
          'btn',
          buttonVariants[variant],
          buttonSizes[size],
          fullWidth && 'w-full',
          className
        )}
        {...animationProps}
        {...props}
      >
        {loading ? (
          <>
            <svg
              className="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Loading...</span>
          </>
        ) : (
          <>
            {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
            {children}
            {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
          </>
        )}
      </Comp>
    );
  }
);

Button.displayName = 'Button';

export default Button;