import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  CheckIcon,
  ClipboardIcon,
  PaperAirplaneIcon,
  StarIcon,
} from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Textarea } from '../../components/ui/Field';
import StatusBadge from '../../components/ui/StatusBadge';
import PriorityBadge from '../../components/ui/PriorityBadge';
import ProgressRail from '../../components/ui/ProgressRail';
import { SkeletonList } from '../../components/ui/Skeleton';
import AttachmentList from '../../components/complaints/AttachmentList';
import Timeline from '../../components/complaints/Timeline';
import { complaintService, errorMessage } from '../../services/api';
import { categoryLabel, getStatus } from '../../utils/status';
import { formatDateTime, formatDeadline, formatRelative, initials } from '../../utils/format';

export default function ComplaintDetails() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => complaintService.get(id),
  });

  const complaint = data?.complaint;
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['complaint', id] });

  const reply = useMutation({
    mutationFn: () => complaintService.reply(id, { message }),
    onSuccess: () => {
      setMessage('');
      setError('');
      refresh();
    },
    onError: (replyError) => setError(errorMessage(replyError, 'We could not send that message.')),
  });

  const rate = useMutation({
    mutationFn: (score) => complaintService.rate(id, score),
    onSuccess: refresh,
  });

  const copyTicket = async () => {
    await navigator.clipboard.writeText(complaint.ticket_number);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-1 py-3 sm:px-4 sm:py-8">
        <SkeletonList rows={4} />
      </div>
    );
  }

  if (!complaint) {
    return (
      <div className="mx-auto max-w-3xl px-1 py-8 text-center sm:px-4 sm:py-16">
        <h1 className="font-display text-xl font-semibold text-ink-900">
          We could not find that complaint.
        </h1>
        <Link to="/student/complaints" className="mt-4 inline-block font-semibold text-brand-700 hover:underline">
          Back to my complaints
        </Link>
      </div>
    );
  }

  const closed = ['resolved', 'closed', 'declined'].includes(complaint.status);

  return (
    <div className="mx-auto max-w-3xl px-1 py-3 sm:px-4 sm:py-8">
      <Link
        to="/student/complaints"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-600 hover:text-brand-700"
      >
        <ArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
        My complaints
      </Link>

      <header className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <button
              type="button"
              onClick={copyTicket}
              className="inline-flex items-center gap-2 font-mono text-sm font-semibold text-ink-600 hover:text-brand-700"
            >
              {complaint.ticket_number}
              {copied ? (
                <CheckIcon className="h-4 w-4" aria-hidden="true" />
              ) : (
                <ClipboardIcon className="h-4 w-4" aria-hidden="true" />
              )}
              <span className="sr-only">Copy ticket number</span>
            </button>
            <h1 className="mt-1 font-display text-xl font-semibold tracking-tight text-ink-900">
              {complaint.title}
            </h1>
            <p className="mt-1 text-sm text-ink-500">
              {categoryLabel(complaint.category)} · filed {formatRelative(complaint.created_at)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={complaint.status} overdue={complaint.is_overdue} />
            <PriorityBadge priority={complaint.priority} />
          </div>
        </div>

        <div className="mt-4 border-t border-line pt-3 sm:mt-5 sm:pt-4">
          <ProgressRail status={complaint.status} />
        </div>

        {!closed && (
          <p className="mt-2 text-sm text-ink-600">
            <span className="text-ink-500">Response due:</span>{' '}
            <strong className="font-semibold text-ink-900">
              {formatDeadline(complaint.resolve_due_at)}
            </strong>
            {complaint.assigned_admin && (
              <>
                {' · '}
                <span className="text-ink-500">Owner:</span>{' '}
                <strong className="font-semibold text-ink-900">
                  {complaint.assigned_admin.full_name}
                </strong>
              </>
            )}
          </p>
        )}

        {complaint.is_escalated && (
          <p
            className="mt-3 rounded-md px-4 py-3 text-sm"
            style={{ backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue-fg)' }}
          >
            This passed its deadline, so it has been raised with senior staff. You do not need to do
            anything.
          </p>
        )}
      </header>

      {complaint.status === 'resolved' && (
        <Outcome
          tone="resolved"
          heading={`Resolved in ${Math.round(complaint.resolution_hours || 0)} hours`}
          body={complaint.resolution_note}
          rating={complaint.satisfaction_rating}
          onRate={(score) => rate.mutate(score)}
        />
      )}

      {complaint.status === 'declined' && (
        <Outcome
          tone="declined"
          heading="Not accepted"
          body={complaint.decline_reason}
          footer="If you disagree, reply below and ask for it to be looked at again."
        />
      )}

      <section className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:mt-5 sm:p-6">
        <h2 className="text-sm font-bold text-ink-900">What you reported</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink-700">
          {complaint.description}
        </p>
      </section>

      {/* The record of movement. Placed above the messages because "has
          anything happened?" is the question a student returns to this
          page to answer. */}
      {complaint.events?.length > 0 && (
        <section className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:mt-5 sm:p-6">
          <h2 className="mb-4 text-sm font-bold text-ink-900 sm:mb-5">What has happened so far</h2>
          <Timeline events={complaint.events} />
        </section>
      )}

      <section className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:mt-5 sm:p-6">
        <AttachmentList
          complaintId={id}
          attachments={complaint.attachments || []}
          canUpload={!closed}
          onChange={refresh}
        />
      </section>

      <section className="mt-4 rounded-lg border border-line bg-surface p-4 shadow-e1 sm:mt-5 sm:p-6">
        <h2 className="mb-4 text-sm font-bold text-ink-900">
          Messages {complaint.responses?.length > 0 && `(${complaint.responses.length})`}
        </h2>

        {(!complaint.responses || complaint.responses.length === 0) && (
          <p className="text-sm text-ink-500">
            No messages yet. You will be notified as soon as someone replies.
          </p>
        )}

        <ol className="space-y-3 sm:space-y-4">
          {complaint.responses?.map((response) => {
            const fromStaff = response.author?.role && response.author.role !== 'student';
            return (
              <li key={response.id} className={`flex gap-3 ${fromStaff ? '' : 'flex-row-reverse'}`}>
                <span
                  className={`flex h-9 w-9 flex-none items-center justify-center rounded-full text-caption font-bold ${
                    fromStaff ? 'bg-brand-100 text-brand-800' : 'bg-line text-ink-600'
                  }`}
                  aria-hidden="true"
                >
                  {initials(response.author?.full_name)}
                </span>
                <div className={`max-w-[80%] ${fromStaff ? '' : 'text-right'}`}>
                  <p className="text-caption font-semibold text-ink-600">
                    {response.author?.full_name || 'Removed account'}
                    {fromStaff && ' · staff'}
                  </p>
                  <div
                    className={`mt-1 whitespace-pre-wrap rounded-lg px-4 py-3 text-sm leading-relaxed ${
                      fromStaff ? 'bg-canvas text-ink-900' : 'bg-brand-700 text-white'
                    }`}
                  >
                    {response.message}
                  </div>
                  <p className="mt-1 text-caption text-ink-500">
                    {formatDateTime(response.created_at)}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>

        {complaint.status !== 'closed' && (
          <div className="mt-4 border-t border-line pt-4 sm:mt-5 sm:pt-5">
            <Textarea
              label="Add a message"
              rows={3}
              placeholder="Add anything that might help, or ask for an update."
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              error={error}
            />
            <div className="mt-3 flex justify-end">
              <Button
                onClick={() => reply.mutate()}
                loading={reply.isPending}
                disabled={message.trim().length < 2}
              >
                <PaperAirplaneIcon className="h-4 w-4" aria-hidden="true" />
                Send
              </Button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function Outcome({ tone, heading, body, footer, rating, onRate }) {
  const config = getStatus(tone);
  return (
    <section
      className="mt-4 rounded-lg p-4 sm:mt-5 sm:p-6"
      style={{ backgroundColor: config.bg, color: config.fg }}
    >
      <h2 className="font-display text-lg font-semibold">{heading}</h2>
      {body && <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{body}</p>}
      {footer && <p className="mt-3 text-caption">{footer}</p>}

      {onRate && (
        <div className="mt-3 border-t pt-3 sm:mt-4 sm:pt-4" style={{ borderColor: 'currentColor', opacity: 0.95 }}>
          {rating ? (
            <p className="text-sm font-semibold">Thank you for rating this {rating} out of 5.</p>
          ) : (
            <>
              <p className="text-sm font-semibold">Was this actually sorted?</p>
              <div className="mt-2 flex gap-1.5">
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    type="button"
                    onClick={() => onRate(score)}
                    className="flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-current"
                    aria-label={`Rate ${score} out of 5`}
                  >
                    <StarIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
