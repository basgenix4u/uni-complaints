import { format, formatDistanceToNow, isValid, parseISO } from 'date-fns';

/** Parses an API timestamp, treating a missing timezone as UTC. */
function parse(value) {
  if (!value) return null;
  const withZone = /[Z+]|-\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = parseISO(withZone);
  return isValid(date) ? date : null;
}

/**
 * Day-first with a written month.
 *
 * A numeric date is read differently in Nigeria and the United States, which
 * is not an acceptable ambiguity on a response deadline.
 */
export function formatDate(value, pattern = 'd MMM yyyy') {
  const date = parse(value);
  return date ? format(date, pattern) : '—';
}

export function formatDateTime(value) {
  return formatDate(value, "d MMM yyyy 'at' HH:mm");
}

export function formatRelative(value) {
  const date = parse(value);
  return date ? formatDistanceToNow(date, { addSuffix: true }) : '—';
}

/** Deadline with the days remaining, or how far it has been missed. */
export function formatDeadline(value) {
  const date = parse(value);
  if (!date) return '—';

  const days = Math.ceil((date - new Date()) / 86400000);
  const stamp = format(date, 'EEE, d MMM yyyy');

  if (days < 0) return `${stamp} · ${Math.abs(days)} day${Math.abs(days) === 1 ? '' : 's'} overdue`;
  if (days === 0) return `${stamp} · today`;
  return `${stamp} · ${days} day${days === 1 ? '' : 's'}`;
}

export function initials(name) {
  return (name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}
