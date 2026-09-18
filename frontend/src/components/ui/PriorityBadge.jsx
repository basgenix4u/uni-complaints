import { PRIORITY } from '../../utils/status';
import { cn } from '../../utils/cn';

// Priority is secondary to status, so it is rendered as a quiet outline
// rather than a filled badge that would compete for attention.
const TONE = {
  low: 'border-line text-ink-500',
  medium: 'border-line text-ink-600',
  high: 'border-[#FDBA74] text-[#B45309] bg-[#FFF7ED]',
  urgent: 'border-[#FCA5A5] text-[#B91C1C] bg-[#FEF2F2]',
};

export default function PriorityBadge({ priority = 'medium', className }) {
  const config = PRIORITY[priority] || PRIORITY.medium;

  return (
    <span
      className={cn(
        'inline-flex h-6 items-center rounded-full border px-2.5 text-caption font-semibold',
        TONE[priority] || TONE.medium,
        className,
      )}
      title={config.hint}
    >
      {config.label}
    </span>
  );
}
