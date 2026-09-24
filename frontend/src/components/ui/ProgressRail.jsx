import { RAIL, getStatus } from '../../utils/status';
import { cn } from '../../utils/cn';

/**
 * Five-node progress indicator.
 *
 * Showing position within the process, rather than a bare status word, keeps
 * people engaged with a case that may take days to resolve.
 */
export default function ProgressRail({ status }) {
  if (status === 'declined') {
    return (
      <div
        className="rounded-lg px-4 py-3 text-sm font-medium"
        style={{ backgroundColor: 'var(--status-declined-bg)', color: 'var(--status-declined-fg)' }}
      >
        This complaint was not accepted. The reason is shown below, and you can appeal.
      </div>
    );
  }

  const current = Math.max(RAIL.indexOf(status), 0);

  return (
    <ol className="flex items-start overflow-visible py-1 sm:py-2" aria-label="Progress">
      {RAIL.map((key, index) => {
        const done = index < current;
        const active = index === current;
        const config = getStatus(key);

        return (
          <li
            key={key}
            className="relative min-w-0 flex-1 px-0.5 text-center sm:min-w-[92px]"
            aria-current={active ? 'step' : undefined}
          >
            {index < RAIL.length - 1 && (
              <span
                className={cn(
                  'absolute left-1/2 top-[13px] z-0 h-0.5 w-full sm:top-[15px]',
                  done ? 'bg-brand-600' : 'bg-line',
                )}
                aria-hidden="true"
              />
            )}
            <span
              className={cn(
                'relative z-10 mx-auto mb-1.5 flex h-7 w-7 items-center justify-center rounded-full border-2 text-[10px] font-bold sm:mb-2 sm:h-8 sm:w-8 sm:text-caption',
                done && 'border-brand-700 bg-brand-700 text-white',
                active && 'border-brand-700 bg-surface text-brand-700 ring-4 ring-brand-100',
                !done && !active && 'border-line bg-surface text-ink-500',
              )}
            >
              {done ? '✓' : index + 1}
            </span>
            <span
              className={cn(
                'block text-[10px] font-semibold leading-tight sm:text-caption',
                done || active ? 'text-ink-900' : 'text-ink-500',
              )}
            >
              {config.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
