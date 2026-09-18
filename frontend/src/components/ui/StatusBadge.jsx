import { getStatus } from '../../utils/status';
import { cn } from '../../utils/cn';

/**
 * Status indicator.
 *
 * The label is rendered unconditionally. Amber and red, and blue and slate,
 * are effectively identical under deuteranopia, so a colour-only badge would
 * leave some users unable to tell "in progress" from "not accepted".
 */
export default function StatusBadge({ status, overdue = false, size = 'md', className }) {
  const config = getStatus(overdue ? 'overdue' : status);
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-semibold whitespace-nowrap',
        size === 'sm' ? 'h-6 px-2.5 text-caption' : 'h-7 px-3 text-sm',
        className,
      )}
      style={{ backgroundColor: config.bg, color: config.fg }}
      title={config.hint}
    >
      <Icon className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} aria-hidden="true" />
      {config.label}
    </span>
  );
}
