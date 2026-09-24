import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { CheckCircleIcon } from '@heroicons/react/24/outline';

import { Select } from '../../components/ui/Field';
import Skeleton from '../../components/ui/Skeleton';
import StatusBadge from '../../components/ui/StatusBadge';
import { categoryLabel } from '../../utils/status';
import { routingService } from '../../services/api';

const WINDOWS = [
  { value: 7, label: 'more than a week' },
  { value: 14, label: 'more than a fortnight' },
  { value: 30, label: 'more than a month' },
  { value: 90, label: 'more than three months' },
];

const days = (iso) => Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);

/**
 * What the institution has not dealt with.
 *
 * Escalation climbs the hierarchy on its own. This is the page for what
 * happens when it reaches the top and still nothing moves. Deliberately
 * not a league table of officers: it is a list of students waiting.
 */
export default function IgnoredComplaints() {
  const [window, setWindow] = useState(7);

  const { data, isLoading } = useQuery({
    queryKey: ['ignored-complaints', window],
    queryFn: () => routingService.ignored(window),
  });

  const complaints = data?.complaints ?? [];

  return (
    <div className="mx-auto max-w-4xl px-1 py-3 sm:px-4 sm:py-8">
      <h1 className="font-display text-xl font-semibold tracking-tight text-ink-900 sm:text-2xl">
        Still waiting
      </h1>
      <p className="mt-1 max-w-xl text-ink-600">
        Complaints that were raised past their deadline, sent up the chain, and still have no
        answer. Each row is a student who has been left without one.
      </p>

      <div className="mt-4 sm:mt-6 max-w-xs">
        <Select
          label="Unanswered for"
          value={window}
          onChange={(event) => setWindow(Number(event.target.value))}
        >
          {WINDOWS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>

      {isLoading && <Skeleton className="mt-4 sm:mt-6 h-48 w-full" />}

      {!isLoading && complaints.length === 0 && (
        <div className="mt-4 sm:mt-6 flex items-start gap-3 rounded-lg border border-line bg-surface p-3 sm:p-6">
          <CheckCircleIcon className="h-6 w-6 shrink-0 text-brand-700" aria-hidden="true" />
          <div>
            <p className="font-medium text-ink-900">Nothing has been left this long.</p>
            <p className="mt-1 text-sm text-ink-600">
              Everything that passed its deadline has since been picked up.
            </p>
          </div>
        </div>
      )}

      {!isLoading && complaints.length > 0 && (
        <>
          <p className="mt-4 sm:mt-6 text-sm font-medium text-ink-700">
            {complaints.length} complaint{complaints.length === 1 ? '' : 's'} waiting.
          </p>
          <ul className="mt-3 space-y-2">
            {complaints.map((complaint) => (
              <li key={complaint.id} className="rounded-lg border border-line bg-surface">
                <Link
                  to={`/admin/complaints/${complaint.id}`}
                  className="flex flex-wrap items-center gap-x-3 gap-y-2 p-4 hover:bg-brand-50/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-ink-900">{complaint.title}</p>
                    <p className="mt-0.5 text-caption text-ink-500">
                      {complaint.ticket_number} · {categoryLabel(complaint.category)}
                      {complaint.department ? ` · ${complaint.department.name}` : ' · unassigned'}
                    </p>
                  </div>
                  <StatusBadge status={complaint.status} />
                  <span className="text-caption font-semibold text-[#B91C1C]">
                    {days(complaint.created_at)} days old
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
