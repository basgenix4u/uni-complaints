import { forwardRef } from 'react';
import { cn } from '../../utils/cn';

const VARIANTS = {
  // Exactly one solid action per screen: when everything is emphasised,
  // nothing is.
  primary: 'bg-brand-700 text-white shadow-e1 hover:bg-brand-800 hover:shadow-e2',
  secondary: 'bg-surface text-ink-700 border border-line hover:border-brand-600 hover:text-brand-700',
  ghost: 'bg-transparent text-ink-600 hover:bg-brand-50 hover:text-brand-700',
  danger: 'bg-[#B91C1C] text-white hover:bg-[#991B1B]',
};

const SIZES = {
  // 44px is the minimum comfortable touch target on a phone.
  md: 'h-11 px-5 text-base',
  sm: 'h-9 px-3.5 text-sm',
  lg: 'h-12 px-6 text-base',
};

const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', loading = false, fullWidth = false, disabled, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-semibold',
        'transition-all duration-150 ease-standard',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none',
        VARIANTS[variant],
        SIZES[size],
        // Was being spread onto the DOM as an unknown attribute and
        // silently doing nothing, so every "full width" button was
        // sitting at its content width.
        fullWidth && 'w-full',
        className,
      )}
      {...props}
    >
      {loading && (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  );
});

export default Button;
