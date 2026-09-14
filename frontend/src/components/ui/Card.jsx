import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

const Card = React.forwardRef(
  (
    {
      children,
      className = '',
      hover = false,
      interactive = false,
      padding = true,
      animate = true,
      delay = 0,
      ...props
    },
    ref
  ) => {
    const Comp = animate ? motion.div : 'div';

    const animationProps = animate
      ? {
          initial: { opacity: 0, y: 20 },
          animate: { opacity: 1, y: 0 },
          transition: {
            duration: 0.4,
            delay,
            ease: [0.25, 0.1, 0.25, 1],
          },
        }
      : {};

    return (
      <Comp
        ref={ref}
        className={cn(
          'bg-white rounded-2xl shadow-soft border border-neutral-100 overflow-hidden',
          hover && 'transition-all duration-300 hover:shadow-soft-xl hover:-translate-y-1 hover:border-primary-100',
          interactive && 'cursor-pointer active:scale-[0.98]',
          padding && 'p-6',
          className
        )}
        {...animationProps}
        {...props}
      >
        {children}
      </Comp>
    );
  }
);

Card.displayName = 'Card';

const CardHeader = ({ children, className = '', ...props }) => (
  <div
    className={cn('flex items-center justify-between mb-4', className)}
    {...props}
  >
    {children}
  </div>
);

const CardTitle = ({ children, className = '', ...props }) => (
  <h3
    className={cn('text-lg font-semibold text-neutral-900', className)}
    {...props}
  >
    {children}
  </h3>
);

const CardDescription = ({ children, className = '', ...props }) => (
  <p className={cn('text-sm text-neutral-500', className)} {...props}>
    {children}
  </p>
);

const CardContent = ({ children, className = '', ...props }) => (
  <div className={cn('', className)} {...props}>
    {children}
  </div>
);

const CardFooter = ({ children, className = '', ...props }) => (
  <div
    className={cn('flex items-center justify-end gap-3 mt-6 pt-4 border-t border-neutral-100', className)}
    {...props}
  >
    {children}
  </div>
);

Card.Header = CardHeader;
Card.Title = CardTitle;
Card.Description = CardDescription;
Card.Content = CardContent;
Card.Footer = CardFooter;

export default Card;