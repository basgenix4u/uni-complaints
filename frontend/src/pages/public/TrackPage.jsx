import { useState } from 'react';
import { Link } from 'react-router-dom';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Field';
import StatusBadge from '../../components/ui/StatusBadge';
import ProgressRail from '../../components/ui/ProgressRail';
import { errorMessage, publicService } from '../../services/api';
import { categoryLabel, getStatus } from '../../utils/status';
import { formatDate, formatDeadline } from '../../utils/format';

/**
 * Ticket lookup without signing in.
 *
 * Someone who has lost their password, or who filed on a shared device,
 * can still see that their complaint exists and where it has reached. The
 * response carries no personal data, so the ticket number alone is safe.
 */
export default function TrackPage() {
  const [ticket, setTicket] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const search = async (event) => {
    event.preventDefault();
    const value = ticket.trim();
    if (!value) {
      setError('Enter the ticket number from your receipt.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const data = await publicService.track(value);
      setResult(data.complaint);
    } catch (requestError) {
      setError(errorMessage(requestError, 'We could not find a complaint with that ticket number.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <div className="text-center">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink-900">
          Track a complaint
        </h1>
        <p className="mx-auto mt-2 max-w-md text-ink-600">
          Enter the ticket number from your receipt. You do not need to sign in.
        </p>
      </div>

      <form onSubmit={search} className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-start">
        <div className="flex-1">
          <Input
            label="Ticket number"
            placeholder="NGX-7K2M-4318"
            value={ticket}
            onChange={(event) => setTicket(event.target.value)}
            error={error}
            hint="Capitals and hyphens are optional."
            className="font-mono"
            autoComplete="off"
          />
        </div>
        <Button type="submit" loading={loading} className="sm:mt-7">
          <MagnifyingGlassIcon className="h-5 w-5" aria-hidden="true" />
          Check
        </Button>
      </form>

      {result && (
        <section className="mt-8 animate-fade-up overflow-hidden rounded-xl border border-line bg-surface shadow-e2">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-canvas px-6 py-5">
            <div>
              <p className="text-caption font-bold uppercase tracking-wider text-ink-500">Ticket</p>
              <p className="font-mono text-lg font-semibold text-ink-900">{result.ticket_number}</p>
            </div>
            <StatusBadge status={result.status} overdue={result.is_overdue} />
          </div>

          <div className="px-6 py-5">
            <ProgressRail status={result.status} />
          </div>

          <dl className="divide-y divide-line border-t border-line text-sm">
            <Row label="Current stage" value={getStatus(result.status).hint} />
            <Row label="Category" value={categoryLabel(result.category)} />
            <Row label="Department" value={result.department || 'Being routed'} />
            <Row label="Filed" value={formatDate(result.created_at)} />
            <Row
              label={result.resolved_at ? 'Resolved' : 'Response due'}
              value={
                result.resolved_at ? formatDate(result.resolved_at) : formatDeadline(result.resolve_due_at)
              }
            />
          </dl>

          <p className="border-t border-line bg-canvas px-6 py-4 text-caption text-ink-500">
            Sign in to read replies, add information, or respond to questions.
          </p>
        </section>
      )}

      <p className="mt-10 text-center text-sm text-ink-500">
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          Sign in
        </Link>{' '}
        to see the full history of your complaints.
      </p>
    </main>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 px-6 py-3">
      <dt className="text-ink-500">{label}</dt>
      <dd className="text-right font-semibold text-ink-900">{value}</dd>
    </div>
  );
}
