import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  LockClosedIcon,
  PaperAirplaneIcon,
} from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Select, Textarea } from '../../components/ui/Field';
import StatusBadge from '../../components/ui/StatusBadge';
import PriorityBadge from '../../components/ui/PriorityBadge';
import ProgressRail from '../../components/ui/ProgressRail';
import { SkeletonList } from '../../components/ui/Skeleton';
import AttachmentList from '../../components/complaints/AttachmentList';
import { complaintService, errorMessage } from '../../services/api';
import { PRIORITY, categoryLabel } from '../../utils/status';
import { formatDateTime, formatDeadline, formatRelative, initials } from '../../utils/format';
import useAuthStore from '../../stores/authStore';

// Mirrors the transitions the server will accept, so the menu never offers
// a move that is rejected.
const NEXT_STATUS = {
  submitted: ['acknowledged', 'in_progress', 'declined'],
  acknowledged: ['in_progress', 'awaiting_student', 'declined'],
  in_progress: ['awaiting_student', 'resolved', 'declined'],
  awaiting_student: ['in_progress', 'resolved', 'declined'],
  resolved: ['closed', 'in_progress'],
  closed: [],
  declined: ['in_progress'],
};

const LABEL = {
  acknowledged: 'Acknowledge',
  in_progress: 'Start work',
  awaiting_student: 'Ask the student for more',
  resolved: 'Mark resolved',
  declined: 'Decline',
  closed: 'Close',
};

export default function AdminComplaintDetails() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const [message, setMessage] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [statusTarget, setStatusTarget] = useState('');
  const [statusNote, setStatusNote] = useState('');
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => complaintService.get(id),
  });

  const { data: staffData } = useQuery({
    queryKey: ['complaint-staff', user?.id],
    queryFn: () => complaintService.staff(),
    enabled: Boolean(user && ['dept_head', 'dean', 'institution_admin', 'platform_admin'].includes(user.role)),
  });

  const complaint = data?.complaint;
  const staff = staffData?.staff || [];
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['complaint', id] });

  const reply = useMutation({
    mutationFn: () => complaintService.reply(id, { message, is_internal: isInternal }),
    onSuccess: () => {
      setMessage('');
      setIsInternal(false);
      setError('');
      refresh();
    },
    onError: (replyError) => setError(errorMessage(replyError)),
  });

  const changeStatus = useMutation({
    mutationFn: () =>
      complaintService.setStatus(id, {
        status: statusTarget,
        note: statusNote,
        reason: statusNote,
      }),
    onSuccess: () => {
      setStatusTarget('');
      setStatusNote('');
      setError('');
      refresh();
    },
    onError: (statusError) => setError(errorMessage(statusError)),
  });

  const assign = useMutation({
    mutationFn: (assignedToId) => complaintService.assign(id, { assigned_to_id: assignedToId }),
    onSuccess: refresh,
    onError: (assignError) => setError(errorMessage(assignError)),
  });

  const changePriority = useMutation({
    mutationFn: (priority) => complaintService.setPriority(id, { priority }),
    onSuccess: refresh,
    onError: (priorityError) => setError(errorMessage(priorityError)),
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <SkeletonList rows={4} />
      </div>
    );
  }

  if (!complaint) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center">
        <h1 className="font-display text-xl font-semibold text-ink-900">
          We could not find that complaint.
        </h1>
        <Link to="/admin/complaints" className="mt-4 inline-block font-semibold text-brand-700 hover:underline">
          Back to complaints
        </Link>
      </div>
    );
  }

  const options = NEXT_STATUS[complaint.status] || [];
  const needsNote = ['resolved', 'declined'].includes(statusTarget);
  const canAssign = ['dept_head', 'dean', 'institution_admin', 'platform_admin'].includes(user?.role);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link
        to="/admin/complaints"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-600 hover:text-brand-700"
      >
        <ArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
        Complaints
      </Link>

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-md px-4 py-3 text-sm font-medium"
          style={{ backgroundColor: 'var(--status-declined-bg)', color: 'var(--status-declined-fg)' }}
        >
          {error}
        </p>
      )}

      <div className="mt-4 grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <header className="rounded-lg border border-line bg-surface p-6 shadow-e1">
            <p className="font-mono text-caption font-semibold text-ink-500">
              {complaint.ticket_number}
            </p>
            <h1 className="mt-1 font-display text-xl font-semibold tracking-tight text-ink-900">
              {complaint.title}
            </h1>
            <p className="mt-1 text-sm text-ink-500">
              {categoryLabel(complaint.category)} · filed {formatRelative(complaint.created_at)}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <StatusBadge status={complaint.status} overdue={complaint.is_overdue} />
              <PriorityBadge priority={complaint.priority} />
            </div>

            <div className="mt-5 border-t border-line pt-4">
              <ProgressRail status={complaint.status} />
            </div>
          </header>

          <section className="rounded-lg border border-line bg-surface p-6 shadow-e1">
            <h2 className="text-sm font-bold text-ink-900">What was reported</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink-700">
              {complaint.description}
            </p>
          </section>

          <section className="rounded-lg border border-line bg-surface p-6 shadow-e1">
            <AttachmentList
              complaintId={id}
              attachments={complaint.attachments || []}
              canUpload={complaint.status !== 'closed'}
              canMarkInternal
              onChange={refresh}
            />
          </section>

          <section className="rounded-lg border border-line bg-surface p-6 shadow-e1">
            <h2 className="mb-4 text-sm font-bold text-ink-900">Thread</h2>

            <ol className="space-y-4">
              {complaint.responses?.map((response) => {
                const fromStaff = response.author?.role && response.author.role !== 'student';
                return (
                  <li key={response.id} className="flex gap-3">
                    <span
                      className={`flex h-9 w-9 flex-none items-center justify-center rounded-full text-caption font-bold ${
                        fromStaff ? 'bg-brand-100 text-brand-800' : 'bg-line text-ink-600'
                      }`}
                      aria-hidden="true"
                    >
                      {initials(response.author?.full_name)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-caption font-semibold text-ink-600">
                        {response.author?.full_name || 'Removed account'}
                        {fromStaff && ' · staff'}
                      </p>
                      <div
                        className="mt-1 whitespace-pre-wrap rounded-lg px-4 py-3 text-sm leading-relaxed"
                        style={
                          response.is_internal
                            ? {
                                backgroundColor: 'var(--status-progress-bg)',
                                color: 'var(--status-progress-fg)',
                              }
                            : { backgroundColor: 'var(--canvas)', color: 'var(--ink-900)' }
                        }
                      >
                        {response.is_internal && (
                          <span className="mb-1.5 flex items-center gap-1.5 text-caption font-bold uppercase tracking-wider">
                            <LockClosedIcon className="h-3.5 w-3.5" aria-hidden="true" />
                            Private — the student cannot see this
                          </span>
                        )}
                        {response.message}
                      </div>
                      <p className="mt-1 text-caption text-ink-500">
                        {formatDateTime(response.created_at)}
                      </p>
                    </div>
                  </li>
                );
              })}
              {!complaint.responses?.length && (
                <p className="text-sm text-ink-500">Nothing on the thread yet.</p>
              )}
            </ol>

            {complaint.status !== 'closed' && (
              <div className="mt-5 border-t border-line pt-5">
                <Textarea
                  label={isInternal ? 'Private note' : 'Reply to the student'}
                  rows={3}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder={
                    isInternal
                      ? 'Only staff will ever see this.'
                      : 'Write plainly. The student will read this.'
                  }
                />

                <div
                  className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md px-3.5 py-2.5"
                  style={
                    isInternal
                      ? {
                          backgroundColor: 'var(--status-progress-bg)',
                          color: 'var(--status-progress-fg)',
                        }
                      : undefined
                  }
                >
                  <label className="inline-flex min-h-touch items-center gap-2.5 text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={isInternal}
                      onChange={(event) => setIsInternal(event.target.checked)}
                      className="h-4 w-4 rounded border-line text-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
                    />
                    <LockClosedIcon className="h-4 w-4" aria-hidden="true" />
                    Keep this private to staff
                  </label>

                  <Button
                    onClick={() => reply.mutate()}
                    loading={reply.isPending}
                    disabled={message.trim().length < 2}
                  >
                    <PaperAirplaneIcon className="h-4 w-4" aria-hidden="true" />
                    {isInternal ? 'Save note' : 'Send reply'}
                  </Button>
                </div>
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-5">
          <section className="rounded-lg border border-line bg-surface p-5 shadow-e1">
            <h2 className="text-sm font-bold text-ink-900">Move this on</h2>
            {options.length === 0 ? (
              <p className="mt-2 text-sm text-ink-500">This complaint is closed.</p>
            ) : (
              <div className="mt-3 space-y-3">
                <Select
                  label="Next step"
                  value={statusTarget}
                  onChange={(event) => setStatusTarget(event.target.value)}
                >
                  <option value="">Choose an action</option>
                  {options.map((option) => (
                    <option key={option} value={option}>
                      {LABEL[option] || option}
                    </option>
                  ))}
                </Select>

                {needsNote && (
                  <Textarea
                    label={statusTarget === 'declined' ? 'Reason' : 'How was it resolved'}
                    required
                    rows={3}
                    value={statusNote}
                    onChange={(event) => setStatusNote(event.target.value)}
                    hint="The student will see this."
                  />
                )}

                <Button
                  className="w-full"
                  disabled={!statusTarget || (needsNote && statusNote.trim().length < 2)}
                  loading={changeStatus.isPending}
                  onClick={() => changeStatus.mutate()}
                >
                  Update
                </Button>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-line bg-surface p-5 shadow-e1">
            <h2 className="text-sm font-bold text-ink-900">Ownership</h2>
            <div className="mt-3 space-y-3">
              {canAssign ? (
                <Select
                  label="Who owns this"
                  value={complaint.assigned_admin?.id || ''}
                  onChange={(event) => assign.mutate(event.target.value || null)}
                >
                  <option value="">Nobody yet</option>
                  {staff.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.full_name}
                    </option>
                  ))}
                </Select>
              ) : (
                <p className="text-sm text-ink-600">
                  {complaint.assigned_admin?.full_name || 'Nobody yet'}
                </p>
              )}

              <Select
                label="Priority"
                value={complaint.priority}
                onChange={(event) => changePriority.mutate(event.target.value)}
                hint="Changing this moves the deadline."
              >
                {Object.entries(PRIORITY).map(([value, config]) => (
                  <option key={value} value={value}>
                    {config.label}
                  </option>
                ))}
              </Select>
            </div>
          </section>

          <section className="rounded-lg border border-line bg-surface p-5 shadow-e1">
            <h2 className="text-sm font-bold text-ink-900">Detail</h2>
            <dl className="mt-3 space-y-2.5 text-sm">
              <Row label="Response due" value={formatDeadline(complaint.resolve_due_at)} />
              <Row label="Department" value={complaint.department?.name || 'Not routed'} />
              {complaint.student ? (
                <>
                  <Row label="Student" value={complaint.student.full_name} />
                  <Row label="Matric" value={complaint.student.matric_number || '—'} />
                  <Row label="Faculty" value={complaint.student.faculty || '—'} />
                </>
              ) : (
                <Row label="Student" value="Filed anonymously" />
              )}
            </dl>
          </section>

          {complaint.events?.length > 0 && (
            <section className="rounded-lg border border-line bg-surface p-5 shadow-e1">
              <h2 className="text-sm font-bold text-ink-900">History</h2>
              <ol className="mt-3 space-y-3">
                {complaint.events.map((event) => (
                  <li key={event.id} className="border-l-2 border-line pl-3 text-caption">
                    <p className="font-semibold text-ink-700">
                      {event.action.replace(/_/g, ' ')}
                      {event.to_value && `: ${event.to_value.replace(/_/g, ' ')}`}
                    </p>
                    <p className="text-ink-500">
                      {event.actor?.full_name || 'System'} · {formatRelative(event.created_at)}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-ink-500">{label}</dt>
      <dd className="text-right font-medium text-ink-900">{value}</dd>
    </div>
  );
}
