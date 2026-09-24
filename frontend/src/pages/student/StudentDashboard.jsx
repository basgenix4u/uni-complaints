import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PlusIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import StatusBadge from '../../components/ui/StatusBadge';
import Skeleton, { SkeletonList } from '../../components/ui/Skeleton';
import { dashboardService } from '../../services/api';
import { categoryLabel } from '../../utils/status';
import { formatDeadline, formatRelative } from '../../utils/format';
import useAuthStore from '../../stores/authStore';

export default function StudentDashboard() {
  const { user } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ['student-stats'],
    queryFn: () => dashboardService.studentStats(),
  });

  const stats = data?.statistics || {};
  const recent = data?.recent_complaints || [];
  const firstName = user?.full_name?.split(' ')[0] || 'there';

  const cards = [
    { label: 'Total filed', value: stats.total, tone: 'text-ink-900' },
    { label: 'Waiting', value: stats.pending, tone: 'text-[#1D4ED8]' },
    { label: 'Being worked on', value: stats.in_progress, tone: 'text-[#B45309]' },
    { label: 'Resolved', value: stats.resolved, tone: 'text-[#046C4E]' },
  ];

  return (
    <div className="mx-auto max-w-4xl px-1 py-5 sm:px-4 sm:py-8">
      <div className="flex flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900">
            Welcome back, {firstName}
          </h1>
          <p className="mt-1 text-ink-600">Here is where your complaints stand.</p>
        </div>
        <Link to="/student/complaints/new">
          <Button>
            <PlusIcon className="h-5 w-5" aria-hidden="true" />
            File a complaint
          </Button>
        </Link>
      </div>

      {stats.awaiting_you > 0 && (
        <p
          className="mt-6 rounded-lg px-4 py-3 text-sm font-medium"
          style={{
            backgroundColor: 'var(--status-acknowledged-bg)',
            color: 'var(--status-acknowledged-fg)',
          }}
        >
          {stats.awaiting_you === 1
            ? 'One complaint is waiting for something from you.'
            : `${stats.awaiting_you} complaints are waiting for something from you.`}{' '}
          <Link to="/student/complaints?status=awaiting_student" className="underline">
            Take a look
          </Link>
        </p>
      )}

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-lg border border-line bg-surface p-4 shadow-e1">
            <p className="text-caption font-bold uppercase tracking-wider text-ink-500">
              {card.label}
            </p>
            {isLoading ? (
              <Skeleton className="mt-2 h-8 w-12" />
            ) : (
              <p className={`mt-1 font-display text-3xl font-semibold ${card.tone}`}>
                {card.value ?? 0}
              </p>
            )}
          </div>
        ))}
      </div>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-ink-900">Recent</h2>
          <Link to="/student/complaints" className="text-sm font-semibold text-brand-700 hover:underline">
            See all
          </Link>
        </div>

        {isLoading && <SkeletonList rows={3} />}

        {!isLoading && recent.length === 0 && (
          <div className="rounded-lg border border-dashed border-line bg-surface px-6 py-12 text-center">
            <h3 className="font-display text-lg font-semibold text-ink-900">No complaints yet</h3>
            <p className="mx-auto mt-1 max-w-sm text-sm text-ink-600">
              When you file one, you will track it here from start to finish.
            </p>
            <Link to="/student/complaints/new" className="mt-5 inline-block">
              <Button>File your first complaint</Button>
            </Link>
          </div>
        )}

        <ul className="space-y-3">
          {recent.map((complaint) => (
            <li key={complaint.id}>
              <Link
                to={`/student/complaints/${complaint.id}`}
                className="block rounded-lg border border-line bg-surface p-4 transition-shadow duration-150 hover:shadow-e2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-caption text-ink-500">{complaint.ticket_number}</p>
                    <h3 className="mt-0.5 truncate font-semibold text-ink-900">{complaint.title}</h3>
                    <p className="mt-1 text-caption text-ink-500">
                      {categoryLabel(complaint.category)} · {formatRelative(complaint.created_at)}
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
      </section>
    </div>
  );
}
