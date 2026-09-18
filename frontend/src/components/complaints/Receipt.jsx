import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckIcon, ClipboardIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';

import Button from '../ui/Button';
import { formatDate, formatDeadline } from '../../utils/format';

/**
 * Confirmation shown immediately after a complaint is filed.
 *
 * This is the moment of highest doubt, when someone is deciding whether the
 * system is real or another form that goes nowhere. It is a full screen
 * rather than a toast so the ticket, the deadline and the escalation promise
 * stay on screen and can be saved.
 */
export default function Receipt({ complaint, institution }) {
  const [copied, setCopied] = useState(false);

  const copyTicket = async () => {
    try {
      await navigator.clipboard.writeText(complaint.ticket_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const deadline = formatDeadline(complaint.resolve_due_at);

  return (
    <div className="mx-auto max-w-xl overflow-hidden rounded-2xl border border-line bg-surface shadow-e4">
      <div className="bg-gradient-to-b from-brand-50 to-transparent px-8 pb-7 pt-10 text-center">
        <span className="mx-auto mb-4 flex h-16 w-16 animate-pop items-center justify-center rounded-full bg-brand-700 shadow-e3">
          <CheckIcon className="h-8 w-8 stroke-[3] text-white" aria-hidden="true" />
        </span>
        <h1 className="font-display text-2xl font-semibold text-ink-900">Your complaint is logged.</h1>
        <p className="mt-1.5 text-ink-600">Keep this ticket. You can check it without signing in.</p>
      </div>

      <div className="mx-8 overflow-hidden rounded-lg border border-line">
        <div className="flex flex-wrap items-center justify-between gap-3 bg-canvas px-5 py-4">
          <div>
            <p className="text-caption font-bold uppercase tracking-wider text-ink-500">Ticket</p>
            <p className="font-mono text-xl font-semibold text-ink-900">{complaint.ticket_number}</p>
          </div>
          <Button variant="secondary" size="sm" onClick={copyTicket}>
            {copied ? (
              <CheckIcon className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ClipboardIcon className="h-4 w-4" aria-hidden="true" />
            )}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>

        <dl className="divide-y divide-line text-sm">
          <Row label="Sent to" value={complaint.department?.name || 'Being routed'} />
          <Row label="Owner" value={complaint.assigned_admin?.full_name || 'Assigning shortly'} />
          <Row label="Respond by" value={deadline} />
          <Row label="Priority" value={complaint.priority} capitalise />
        </dl>
      </div>

      <div className="px-8 pb-6 pt-7">
        <h2 className="mb-3.5 text-sm font-bold text-ink-900">What happens next</h2>
        <ol className="space-y-3">
          <Step n={1}>
            {institution?.name || 'The department'} acknowledges your complaint
          </Step>
          <Step n={2}>A named officer takes ownership</Step>
          <Step n={3}>You get an update here as soon as anything changes</Step>
        </ol>

        <p className="mt-4 flex gap-2.5 rounded-md border border-brand-200 bg-brand-50 px-4 py-3 text-sm leading-relaxed text-brand-900">
          <ShieldCheckIcon className="h-5 w-5 flex-none" aria-hidden="true" />
          <span>
            <strong className="font-semibold">
              If nobody responds by {formatDate(complaint.resolve_due_at)}, this escalates automatically.
            </strong>{' '}
            You do not have to chase it.
          </span>
        </p>
      </div>

      <div className="flex flex-wrap gap-3 px-8 pb-8">
        <Link to={`/complaints/${complaint.id}`} className="flex-1">
          <Button className="w-full">Track this complaint</Button>
        </Link>
        <Link to="/complaints" className="flex-1">
          <Button variant="secondary" className="w-full">
            Back to my complaints
          </Button>
        </Link>
      </div>
    </div>
  );
}

function Row({ label, value, capitalise = false }) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-3">
      <dt className="text-ink-500">{label}</dt>
      <dd className={`text-right font-semibold text-ink-900 ${capitalise ? 'capitalize' : ''}`}>
        {value}
      </dd>
    </div>
  );
}

function Step({ n, children }) {
  return (
    <li className="flex gap-3 text-sm leading-relaxed text-ink-600">
      <span className="mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full bg-brand-50 text-caption font-bold text-brand-800">
        {n}
      </span>
      {children}
    </li>
  );
}
