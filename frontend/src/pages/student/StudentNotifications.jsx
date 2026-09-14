import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  BellIcon,
  CheckIcon,
  DocumentTextIcon,
  ChatBubbleLeftIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Spinner, EmptyState, PageHeader } from '../../components/ui';
import { studentService } from '../../services/api';
import { formatRelativeTime } from '../../utils/helpers';
import { cn } from '../../utils/cn';

const notificationIcons = {
  complaint_submitted: DocumentTextIcon,
  status_changed: ArrowPathIcon,
  new_response: ChatBubbleLeftIcon,
  complaint_resolved: CheckIcon,
  default: BellIcon,
};

const StudentNotifications = () => {
  const queryClient = useQueryClient();

  // Fetch notifications
  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => studentService.getNotifications({ per_page: 50 }),
  });

  const notifications = data?.data?.notifications || [];
  const unreadCount = notifications.filter(n => !n.is_read).length;

  // Mark as read mutation
  const markReadMutation = useMutation({
    mutationFn: (id) => studentService.markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['notifications']);
    },
  });

  // Mark all as read mutation
  const markAllReadMutation = useMutation({
    mutationFn: () => studentService.markAllNotificationsRead(),
    onSuccess: () => {
      toast.success('All notifications marked as read');
      queryClient.invalidateQueries(['notifications']);
    },
  });

  const handleMarkRead = (id) => {
    markReadMutation.mutate(id);
  };

  return (
    <div className="max-w-3xl mx-auto">
      <PageHeader
        title="Notifications"
        description={unreadCount > 0 ? `You have ${unreadCount} unread notification${unreadCount !== 1 ? 's' : ''}` : 'All caught up!'}
        action={
          unreadCount > 0 && (
            <Button
              variant="outline"
              onClick={() => markAllReadMutation.mutate()}
              loading={markAllReadMutation.isPending}
              leftIcon={<CheckIcon className="w-4 h-4" />}
            >
              Mark All as Read
            </Button>
          )
        }
      />

      <Card padding={false}>
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : notifications.length === 0 ? (
          <EmptyState
            icon={BellIcon}
            title="No notifications"
            description="You don't have any notifications yet. We'll notify you when there are updates to your complaints."
          />
        ) : (
          <div className="divide-y divide-neutral-100">
            {notifications.map((notification, index) => {
              const IconComponent = notificationIcons[notification.type] || notificationIcons.default;
              
              return (
                <motion.div
                  key={notification.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={cn(
                    'p-4 sm:p-6 hover:bg-neutral-50 transition-colors',
                    !notification.is_read && 'bg-primary-50/50'
                  )}
                >
                  <div className="flex gap-4">
                    {/* Icon */}
                    <div className={cn(
                      'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
                      notification.is_read ? 'bg-neutral-100' : 'bg-primary-100'
                    )}>
                      <IconComponent className={cn(
                        'w-5 h-5',
                        notification.is_read ? 'text-neutral-500' : 'text-primary-600'
                      )} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className={cn(
                            'font-medium',
                            notification.is_read ? 'text-neutral-700' : 'text-neutral-900'
                          )}>
                            {notification.title}
                          </p>
                          <p className="text-sm text-neutral-500 mt-0.5">
                            {notification.message}
                          </p>
                          <p className="text-xs text-neutral-400 mt-2">
                            {formatRelativeTime(notification.created_at)}
                          </p>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {!notification.is_read && (
                            <button
                              onClick={() => handleMarkRead(notification.id)}
                              className="p-2 rounded-lg text-neutral-400 hover:text-primary-600 hover:bg-primary-50 transition-colors"
                              title="Mark as read"
                            >
                              <CheckIcon className="w-4 h-4" />
                            </button>
                          )}
                          {notification.complaint_id && (
                            <Link
                              to={`/student/complaints/${notification.complaint_id}`}
                              className="text-sm font-medium text-primary-600 hover:text-primary-700"
                            >
                              View
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Unread Indicator */}
                    {!notification.is_read && (
                      <div className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0 mt-2" />
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
};

export default StudentNotifications;