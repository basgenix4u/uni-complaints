import { forwardRef, useId } from 'react';
import { cn } from '../../utils/cn';

/**
 * Labelled form control.
 *
 * The label is a real element rather than a placeholder, and errors are
 * announced through aria-live so they reach screen readers.
 */
function useFieldIds(explicitId) {
  const generated = useId();
  const id = explicitId || generated;
  return { id, errorId: `${id}-error`, hintId: `${id}-hint` };
}

const base =
  'w-full rounded-md border bg-surface px-3.5 text-base text-ink-900 placeholder:text-ink-500 ' +
  'transition-colors duration-150 ease-standard ' +
  'focus:outline-2 focus:outline-offset-2 focus:outline-brand-700 ' +
  'disabled:opacity-60 disabled:cursor-not-allowed';

function Shell({ label, hint, error, required, children, ids, labelHidden = false }) {
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={ids.id}
        className={cn(
          'block text-sm font-semibold text-ink-700',
          labelHidden && 'sr-only',
        )}
      >
        {label}
        {required && (
          <span className="text-[#B91C1C]" aria-hidden="true">
            {' '}
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && (
        <p id={ids.hintId} className="text-caption text-ink-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={ids.errorId} role="alert" aria-live="polite" className="text-caption font-medium text-[#B91C1C]">
          {error}
        </p>
      )}
    </div>
  );
}

export const Input = forwardRef(function Input(
  {
    label,
    labelHidden = false,
    hint,
    error,
    required,
    id,
    className,
    leftIcon,
    rightSlot,
    ...props
  },
  ref,
) {
  const ids = useFieldIds(id);
  const field = (
    <input
      ref={ref}
      id={ids.id}
      aria-invalid={error ? 'true' : undefined}
      aria-describedby={error ? ids.errorId : hint ? ids.hintId : undefined}
      className={cn(
        base,
        'h-11',
        // Room for whatever sits inside the field, so the caret never
        // runs underneath it.
        leftIcon && 'pl-10',
        rightSlot && 'pr-11',
        error ? 'border-[#B91C1C]' : 'border-line',
        className,
      )}
      {...props}
    />
  );

  return (
    <Shell
      label={label}
      labelHidden={labelHidden}
      hint={hint}
      error={error}
      required={required}
      ids={ids}
    >
      {leftIcon || rightSlot ? (
        <div className="relative">
          {leftIcon && (
            <span
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 flex -translate-y-1/2 text-ink-500"
            >
              {leftIcon}
            </span>
          )}
          {field}
          {rightSlot && (
            <span className="absolute right-1 top-1/2 flex -translate-y-1/2">{rightSlot}</span>
          )}
        </div>
      ) : (
        field
      )}
    </Shell>
  );
});

export const Textarea = forwardRef(function Textarea(
  { label, hint, error, required, id, rows = 5, className, ...props },
  ref,
) {
  const ids = useFieldIds(id);
  return (
    <Shell label={label} hint={hint} error={error} required={required} ids={ids}>
      <textarea
        ref={ref}
        id={ids.id}
        rows={rows}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error ? ids.errorId : hint ? ids.hintId : undefined}
        className={cn(base, 'py-2.5 leading-relaxed', error ? 'border-[#B91C1C]' : 'border-line', className)}
        {...props}
      />
    </Shell>
  );
});

export const Select = forwardRef(function Select(
  { label, hint, error, required, id, children, className, ...props },
  ref,
) {
  const ids = useFieldIds(id);
  return (
    <Shell label={label} hint={hint} error={error} required={required} ids={ids}>
      <select
        ref={ref}
        id={ids.id}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error ? ids.errorId : hint ? ids.hintId : undefined}
        className={cn(base, 'h-11', error ? 'border-[#B91C1C]' : 'border-line', className)}
        {...props}
      >
        {children}
      </select>
    </Shell>
  );
});
