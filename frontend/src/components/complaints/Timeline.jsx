import {
  ArrowUpCircleIcon,
  CheckCircleIcon,
  DocumentPlusIcon,
  FlagIcon,
  PaperAirplaneIcon,
  StarIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';

import { formatDateTime, formatRelative } from '../../utils/format';
import { getStatus } from '../../utils/status';

/**
 * What has happened to this complaint, oldest first.
 *
 * This is the product's promise made visible: not "submitted", but a
 * record that somebody routed it, somebody picked it up, somebody
 * changed its state — each with a time. A complaint that has visibly
 * moved is one the student does not need to chase; one that has visibly
 * not moved is exactly what the escalation ladder is for.
 */

function describe(event) {
  const to = event.to_value;
  const from = event.from_value;

  switch (event.action) {
    case 'created':
      return { icon: PaperAirplaneIcon, text: 'Filed', detail: event.note };
    case 'status_changed':
      return {
        icon: CheckCircleIcon,
        text: `Status moved to ${getStatus(to)?.label || to}`,
        detail: event.note,
      };
    case 'assigned':
      return { icon: UserCircleIcon, text: `Picked up${to ? ` by ${to}` : ''}` };
    case 'unassigned':
      return { icon: UserCircleIcon, text: 'Returned to the queue' };
    case 'priority_changed':
      return { icon: FlagIcon, text: `Priority changed from ${from} to ${to}` };
    case 'attached':
      return { icon: DocumentPlusIcon, text: `File added${to ? `: ${to}` : ''}` };
    case 'attachment_removed':
      return { icon: DocumentPlusIcon, text: `File removed${from ? `: ${from}` : ''}` };
    case 'rated':
      return { icon: StarIcon, text: `Rated ${to} out of 5` };
    case 'escalated':
      return {
        icon: ArrowUpCircleIcon,
        text: 'Escalated up the chain',
        detail: 'The deadline passed, so this moved to someone more senior.',
      };
    default:
      // An action this component does not know yet still deserves a row;
      // hiding it would make the timeline quietly incomplete.
      return { icon: CheckCircleIcon, text: event.action.replaceAll('_', ' ') };
  }
}

export default function Timeline({ events }) {
  if (!events?.length) return null;

  const ordered = [...events].sort(
    (a, b) => new Date(a.created_at) - new Date(b.created_at),
  );

  return (
    <ol className="relative space-y-4 border-l-2 border-line pl-5 sm:space-y-6 sm:pl-6">
      {ordered.map((event, index) => {
        const { icon: Icon, text, detail } = describe(event);
        const latest = index === ordered.length - 1;
        return (
          <li key={event.id} className="relative">
            <span
              className={`absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full ring-4 ring-surface ${
                latest ? 'bg-brand-700 text-white' : 'bg-brand-50 text-brand-700'
              }`}
              aria-hidden="true"
            >
              <Icon className="h-4 w-4" />
            </span>
            <p className="text-sm font-semibold text-ink-900">{text}</p>
            {detail && <p className="mt-0.5 text-sm text-ink-600">{detail}</p>}
            <p className="mt-0.5 text-caption text-ink-500">
              <time dateTime={event.created_at} title={formatDateTime(event.created_at)}>
                {formatRelative(event.created_at)}
              </time>
            </p>
          </li>
        );
      })}
    </ol>
  );
}
