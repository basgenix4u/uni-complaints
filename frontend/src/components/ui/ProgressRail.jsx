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
    <ol className="flex items-start overflow-x-auto py-2" aria-label="Progress">
      {RAIL.map((key, index) => {
        const done = index < current;
        const active = index === current;
        const config = getStatus(key);

        return (
          <li
            key={key}
            className="relative min-w-[72px] flex-1 px-0.5 text-center sm:min-w-[92px]"
            aria-current={active ? 'step' : undefined}
          >
            {index < RAIL.length - 1 && (
              <span
                className={cn(
                  'absolute left-1/2 top-[15px] z-0 h-0.5 w-full',
                  done ? 'bg-brand-600' : 'bg-line',
                )}
                aria-hidden="true"
              />
            )}
            <span
              className={cn(
                'relative z-10 mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-full border-2 text-caption font-bold',
                done && 'border-brand-700 bg-brand-700 text-white',
                active && 'border-brand-700 bg-surface text-brand-700 ring-4 ring-brand-100',
                !done && !active && 'border-line bg-surface text-ink-500',
              )}
            >
              {done ? '✓' : index + 1}
            </span>
            <span
              className={cn(
                'block text-caption font-semibold',
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
