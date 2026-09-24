import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BellIcon, CheckIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { SkeletonList } from '../../components/ui/Skeleton';
import { notificationService } from '../../services/api';
import { formatRelative } from '../../utils/format';
import useAuthStore from '../../stores/authStore';

const TONE = {
  escalation: { bg: 'var(--status-overdue-bg)', fg: 'var(--status-overdue-fg)' },
  response: { bg: 'var(--status-submitted-bg)', fg: 'var(--status-submitted-fg)' },
  assignment: { bg: 'var(--status-acknowledged-bg)', fg: 'var(--status-acknowledged-fg)' },
  submitted: { bg: 'var(--status-resolved-bg)', fg: 'var(--status-resolved-fg)' },
};

export default function StudentNotifications() {
  const { isAdmin } = useAuthStore();
  const queryClient = useQueryClient();
  const complaintBasePath = isAdmin() ? '/admin' : '/student';

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationService.list({ per_page: 50 }),
  });

  const notifications = data?.notifications || [];
  const unread = data?.unread_count || 0;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
    queryClient.invalidateQueries({ queryKey: ['nav-notifications'] });
    queryClient.invalidateQueries({ queryKey: ['nav-unread-count'] });
  };

  const markOne = useMutation({
    mutationFn: (id) => notificationService.markRead(id),
    // Applied immediately and reconciled afterwards, so the list responds
    // at once rather than after a round trip.
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['notifications'] });
      const previous = queryClient.getQueryData(['notifications']);
      queryClient.setQueryData(['notifications'], (current) =>
        current
          ? {
              ...current,
              unread_count: Math.max((current.unread_count || 1) - 1, 0),
              notifications: current.notifications.map((item) =>
                item.id === id ? { ...item, is_read: true } : item,
              ),
            }
          : current,
      );
      return { previous };
    },
    onError: (_error, _id, context) =>
      queryClient.setQueryData(['notifications'], context?.previous),
    onSettled: invalidate,
  });

  const markAll = useMutation({
    mutationFn: () => notificationService.markAllRead(),
    onSuccess: invalidate,
  });

  return (
    <div className="mx-auto max-w-2xl px-1 py-3 sm:px-4 sm:py-8">
      <div className="flex flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="font-display text-xl font-semibold tracking-tight sm:text-2xl text-ink-900">
            Notifications
          </h1>
          <p className="mt-1 text-ink-600">
            {unread > 0 ? `${unread} unread` : 'You are up to date.'}
          </p>
        </div>
        {unread > 0 && (
          <Button variant="secondary" size="sm" loading={markAll.isPending} onClick={() => markAll.mutate()}>
            <CheckIcon className="h-4 w-4" aria-hidden="true" />
            Mark all as read
          </Button>
        )}
      </div>

      <div className="mt-4 sm:mt-6">
        {isLoading && <SkeletonList rows={4} />}

        {!isLoading && notifications.length === 0 && (
          <div className="rounded-lg border border-dashed border-line bg-surface px-4 py-10 text-center sm:px-6 sm:py-16">
            <BellIcon className="mx-auto h-10 w-10 text-ink-500" aria-hidden="true" />
            <h2 className="mt-3 font-display text-lg font-semibold text-ink-900">
              Nothing to catch up on
            </h2>
            <p className="mt-1 text-sm text-ink-600">
              We will let you know as soon as anything changes on your complaints.
            </p>
          </div>
        )}

        <ul className="space-y-2">
          {notifications.map((notification) => {
            const tone = TONE[notification.type] || {
              bg: 'var(--status-closed-bg)',
              fg: 'var(--status-closed-fg)',
            };
            const body = (
              <div
                className={`flex gap-3 rounded-lg border p-3 text-left sm:p-4 transition-colors duration-150 ${
                  notification.is_read
                    ? 'border-line bg-surface'
                    : 'border-brand-200 bg-brand-50'
                }`}
              >
                <span
                  className="mt-0.5 flex h-8 w-8 flex-none items-center justify-center rounded-full"
                  style={{ backgroundColor: tone.bg, color: tone.fg }}
                  aria-hidden="true"
                >
                  <BellIcon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-ink-900">{notification.title}</p>
                  <p className="mt-0.5 text-sm text-ink-600">{notification.message}</p>
                  <p className="mt-1 text-caption text-ink-500">
                    {formatRelative(notification.created_at)}
                  </p>
                </div>
                {!notification.is_read && (
                  <span
                    className="mt-1.5 h-2 w-2 flex-none rounded-full bg-brand-700"
                    aria-label="Unread"
                  />
                )}
              </div>
            );

            return (
              <li key={notification.id}>
                {notification.complaint_id ? (
                  <Link
                    to={`${complaintBasePath}/complaints/${notification.complaint_id}`}
                    onClick={() => !notification.is_read && markOne.mutate(notification.id)}
                    className="block rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
                  >
                    {body}
                  </Link>
                ) : (
                  <button
                    type="button"
                    onClick={() => !notification.is_read && markOne.mutate(notification.id)}
                    className="block w-full rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
                  >
                    {body}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
