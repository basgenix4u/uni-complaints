import { useState } from 'react';
import { Link } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { InboxIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/Field';
import StatusBadge from '../../components/ui/StatusBadge';
import PriorityBadge from '../../components/ui/PriorityBadge';
import { SkeletonList } from '../../components/ui/Skeleton';
import { complaintService } from '../../services/api';
import { PRIORITY, STATUS, categoryLabel } from '../../utils/status';
import { formatDeadline, formatRelative } from '../../utils/format';

// Saved views cover the questions staff actually open this screen to ask.
const VIEWS = [
  { key: 'all', label: 'Everything', params: {} },
  { key: 'unassigned', label: 'Unassigned', params: { unassigned: '1' } },
  { key: 'overdue', label: 'Overdue', params: { overdue: '1' } },
  { key: 'mine', label: 'Mine', params: { scope: 'mine' } },
];

export default function AdminComplaints() {
  const [view, setView] = useState('all');
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [search, setSearch] = useState('');

  const viewParams = VIEWS.find((entry) => entry.key === view)?.params || {};

  const { data, isLoading } = useQuery({
    queryKey: ['admin-complaints', { view, page, status, priority, search }],
    queryFn: () =>
      complaintService.list({ page, per_page: 10, status, priority, search, ...viewParams }),
    placeholderData: keepPreviousData,
  });

  const complaints = data?.complaints || [];
  const pagination = data?.pagination || {};

  const changeView = (key) => {
    setView(key);
    setPage(1);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900">Complaints</h1>
      <p className="mt-1 text-ink-600">Triage, assign and respond.</p>

      <div className="mt-6 flex flex-wrap gap-2" role="tablist" aria-label="Saved views">
        {VIEWS.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            aria-selected={view === entry.key}
            onClick={() => changeView(entry.key)}
            className={`min-h-touch rounded-md border px-4 text-sm font-semibold transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700 ${
              view === entry.key
                ? 'border-brand-700 bg-brand-50 text-brand-800'
                : 'border-line bg-surface text-ink-600 hover:border-brand-600'
            }`}
          >
            {entry.label}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <div className="min-w-[220px] flex-1">
          <Input
            label="Search"
            placeholder="Title, ticket or description"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="min-w-[170px]">
          <Select
            label="Status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Any status</option>
            {Object.entries(STATUS)
              .filter(([key]) => key !== 'overdue')
              .map(([key, config]) => (
                <option key={key} value={key}>
                  {config.label}
                </option>
              ))}
          </Select>
        </div>
        <div className="min-w-[150px]">
          <Select
            label="Priority"
            value={priority}
            onChange={(event) => {
              setPriority(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Any priority</option>
            {Object.entries(PRIORITY).map(([key, config]) => (
              <option key={key} value={key}>
                {config.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="mt-6">
        {isLoading && <SkeletonList rows={6} />}

        {!isLoading && complaints.length === 0 && (
          <div className="rounded-lg border border-dashed border-line bg-surface px-6 py-16 text-center">
            <InboxIcon className="mx-auto h-10 w-10 text-ink-500" aria-hidden="true" />
            <h2 className="mt-3 font-display text-lg font-semibold text-ink-900">
              Nothing here
            </h2>
            <p className="mt-1 text-sm text-ink-600">
              {view === 'unassigned'
                ? 'Every complaint has an owner.'
                : view === 'overdue'
                  ? 'Nothing has passed its deadline.'
                  : 'No complaints match these filters.'}
            </p>
          </div>
        )}

        {complaints.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-line bg-surface shadow-e1">
            <table className="w-full text-sm">
              <caption className="sr-only">Complaints</caption>
              <thead>
                <tr className="border-b border-line">
                  <Th>Ticket</Th>
                  <Th>Complaint</Th>
                  <Th>Status</Th>
                  <Th className="hidden md:table-cell">Priority</Th>
                  <Th className="hidden lg:table-cell">Owner</Th>
                  <Th className="hidden sm:table-cell">Due</Th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((complaint) => (
                  <tr key={complaint.id} className="border-b border-line last:border-0 hover:bg-canvas">
                    <td className="px-4 py-3 align-middle">
                      <Link
                        to={`/admin/complaints/${complaint.id}`}
                        className="font-mono text-caption font-semibold text-brand-700 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
                      >
                        {complaint.ticket_number}
                      </Link>
                    </td>
                    <td className="max-w-xs px-4 py-3 align-middle">
                      <Link to={`/admin/complaints/${complaint.id}`} className="block">
                        <span className="block truncate font-medium text-ink-900">
                          {complaint.title}
                        </span>
                        <span className="block text-caption text-ink-500">
                          {categoryLabel(complaint.category)} ·{' '}
                          {formatRelative(complaint.created_at)}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3 align-middle">
                      <StatusBadge
                        status={complaint.status}
                        overdue={complaint.is_overdue}
                        size="sm"
                      />
                    </td>
                    <td className="hidden px-4 py-3 align-middle md:table-cell">
                      <PriorityBadge priority={complaint.priority} />
                    </td>
                    <td className="hidden px-4 py-3 align-middle text-ink-600 lg:table-cell">
                      {complaint.assigned_admin?.full_name || (
                        <span className="text-ink-500">Unassigned</span>
                      )}
                    </td>
                    <td className="hidden px-4 py-3 align-middle text-caption sm:table-cell">
                      <span className={complaint.is_overdue ? 'font-semibold text-[#9F1239]' : 'text-ink-600'}>
                        {['resolved', 'closed', 'declined'].includes(complaint.status)
                          ? '—'
                          : formatDeadline(complaint.resolve_due_at)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {pagination.total_pages > 1 && (
          <nav className="mt-6 flex items-center justify-between" aria-label="Pages">
            <Button
              variant="secondary"
              size="sm"
              disabled={!pagination.has_prev}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </Button>
            <p className="text-sm text-ink-600">
              Page {pagination.page} of {pagination.total_pages} · {pagination.total_items} total
            </p>
            <Button
              variant="secondary"
              size="sm"
              disabled={!pagination.has_next}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </nav>
        )}
      </div>
    </div>
  );
}

function Th({ children, className = '' }) {
  return (
    <th
      scope="col"
      className={`px-4 py-3 text-left text-caption font-bold uppercase tracking-wider text-ink-500 ${className}`}
    >
      {children}
    </th>
  );
}
