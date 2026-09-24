import { useState } from 'react';
import { Link } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { MagnifyingGlassIcon, PlusIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/Field';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonList } from '../../components/ui/Skeleton';
import { complaintService } from '../../services/api';
import { STATUS, categoryLabel } from '../../utils/status';
import { formatDeadline, formatRelative } from '../../utils/format';

export default function MyComplaints() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['complaints', { page, status, search }],
    queryFn: () => complaintService.list({ page, per_page: 10, status, search }),
    // Keeps the previous page on screen while the next one loads, so the
    // layout does not collapse on a slow connection.
    placeholderData: keepPreviousData,
  });

  const complaints = data?.complaints || [];
  const pagination = data?.pagination || {};

  return (
    <div className="mx-auto max-w-4xl px-1 py-5 sm:px-4 sm:py-8">
      <div className="flex flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900">
            My complaints
          </h1>
          <p className="mt-1 text-ink-600">Everything you have filed, and where it has reached.</p>
        </div>
        <Link to="/student/complaints/new">
          <Button>
            <PlusIcon className="h-5 w-5" aria-hidden="true" />
            File a complaint
          </Button>
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <div className="min-w-[220px] flex-1">
          <Input
            label="Search"
            placeholder="Title or ticket number"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="min-w-[180px]">
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
      </div>

      <div className="mt-6">
        {isLoading && <SkeletonList rows={5} />}

        {!isLoading && complaints.length === 0 && (
          <div className="rounded-lg border border-dashed border-line bg-surface px-6 py-16 text-center">
            <MagnifyingGlassIcon className="mx-auto h-10 w-10 text-ink-500" aria-hidden="true" />
            <h2 className="mt-3 font-display text-lg font-semibold text-ink-900">
              {search || status ? 'Nothing matches that' : 'No complaints yet'}
            </h2>
            <p className="mx-auto mt-1 max-w-sm text-sm text-ink-600">
              {search || status
                ? 'Try a different search or clear the filters.'
                : 'When you file one, you will track it here from start to finish.'}
            </p>
            {!search && !status && (
              <Link to="/student/complaints/new" className="mt-5 inline-block">
                <Button>File your first complaint</Button>
              </Link>
            )}
          </div>
        )}

        <ul className="space-y-3">
          {complaints.map((complaint) => (
            <li key={complaint.id}>
              <Link
                to={`/student/complaints/${complaint.id}`}
                className="block rounded-lg border border-line bg-surface p-4 transition-shadow duration-150 hover:shadow-e2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-caption text-ink-500">{complaint.ticket_number}</p>
                    <h2 className="mt-0.5 truncate font-semibold text-ink-900">{complaint.title}</h2>
                    <p className="mt-1 text-caption text-ink-500">
                      {categoryLabel(complaint.category)} · {formatRelative(complaint.created_at)}
                      {complaint.response_count > 0 &&
                        ` · ${complaint.response_count} ${
                          complaint.response_count === 1 ? 'reply' : 'replies'
                        }`}
                    </p>
                  </div>
                  <StatusBadge status={complaint.status} overdue={complaint.is_overdue} size="sm" />
                </div>

                {!['resolved', 'closed', 'declined'].includes(complaint.status) && (
                  <p className="mt-2 text-caption text-ink-500">
                    Response: {formatDeadline(complaint.resolve_due_at)}
                  </p>
                )}
              </Link>
            </li>
          ))}
        </ul>

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
              Page {pagination.page} of {pagination.total_pages}
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
