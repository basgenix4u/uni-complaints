import React, { Fragment } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Menu, Transition } from '@headlessui/react';
import {
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  BellIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  UserCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

import Avatar from '../ui/Avatar';
import useAuthStore from '../../stores/authStore';
import { notificationService } from '../../services/api';
import { formatRelative } from '../../utils/format';
import { cn } from '../../utils/cn';

const ROLE_LABELS = {
  student: 'Student',
  officer: 'Officer',
  dept_head: 'Department head',
  dean: 'Dean',
  institution_admin: 'Administrator',
  platform_admin: 'Platform owner',
};

const openCommandPalette = () => {
  window.dispatchEvent(new Event('resolve:open-command-palette'));
};

const Navbar = ({ isMenuOpen = false, onMenuClick, title }) => {
  const { user, logout, isAdmin } = useAuthStore();
  const notificationPath = isAdmin() ? '/admin/notifications' : '/student/notifications';
  const profilePath = isAdmin() ? '/admin/settings' : '/student/profile';

  const { data: notificationData, isLoading: notificationsLoading } = useQuery({
    queryKey: ['nav-notifications', user?.id],
    queryFn: () => notificationService.list({ per_page: 3 }),
    enabled: Boolean(user),
    staleTime: 30_000,
  });

  const notifications = notificationData?.notifications || [];
  const unread = notificationData?.unread_count || 0;

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface backdrop-blur-xl">
      <div className="flex min-h-14 items-center justify-between gap-1 px-2.5 sm:min-h-16 sm:gap-1.5 sm:px-6 lg:px-8">
        {/* Left section */}
        <div className="flex min-w-0 items-center gap-1 sm:gap-4">
          <button
            type="button"
            onClick={onMenuClick}
            aria-label={isMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={isMenuOpen}
            aria-controls="mobile-navigation"
            className="inline-flex min-h-touch min-w-touch items-center justify-center rounded-md text-ink-600 transition-colors hover:bg-canvas hover:text-ink-900 lg:hidden"
          >
            {isMenuOpen ? (
              <XMarkIcon className="h-6 w-6" aria-hidden="true" />
            ) : (
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            )}
          </button>

          <div className="min-w-0 max-w-[34vw] sm:max-w-none">
            <h1 className="truncate text-sm font-semibold text-ink-900 sm:text-xl">{title}</h1>
          </div>
        </div>

        {/* Search opens the same keyboard-friendly command palette on every breakpoint. */}
        <button
          type="button"
          onClick={openCommandPalette}
          aria-label="Search complaints or jump to a page"
          className="hidden min-h-11 min-w-0 max-w-md flex-1 items-center gap-3 rounded-md bg-canvas px-3 text-left text-sm text-ink-500 transition-colors hover:bg-brand-50 hover:text-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700 md:flex md:mx-4 lg:mx-8"
        >
          <MagnifyingGlassIcon className="h-5 w-5 flex-none" aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">Search complaints or jump to a page</span>
          <kbd className="hidden flex-none rounded border border-line bg-surface px-1.5 py-0.5 font-mono text-caption text-ink-500 lg:block">
            Ctrl K
          </kbd>
        </button>

        {/* Right section */}
        <div className="flex flex-none items-center gap-0.5 sm:gap-2">
          <button
            type="button"
            onClick={openCommandPalette}
            aria-label="Search complaints or jump to a page"
            className="inline-flex min-h-touch min-w-touch items-center justify-center rounded-md text-ink-600 transition-colors hover:bg-canvas hover:text-ink-900 md:hidden"
          >
            <MagnifyingGlassIcon className="h-5 w-5" aria-hidden="true" />
          </button>

          <Menu as="div" className="relative">
            <Menu.Button
              aria-label={unread ? `${unread} unread notifications` : 'Notifications'}
              className="relative inline-flex min-h-touch min-w-touch items-center justify-center rounded-md text-ink-600 transition-colors hover:bg-canvas hover:text-ink-900"
            >
              <BellIcon className="h-5 w-5 sm:h-6 sm:w-6" aria-hidden="true" />
              {unread > 0 && (
                <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#B91C1C] px-1 text-[10px] font-bold leading-none text-white ring-2 ring-surface">
                  {unread > 99 ? '99+' : unread}
                </span>
              )}
            </Menu.Button>

            <Transition
              as={Fragment}
              enter="transition ease-out duration-150"
              enterFrom="opacity-0 translate-y-1 scale-95"
              enterTo="opacity-100 translate-y-0 scale-100"
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100 translate-y-0 scale-100"
              leaveTo="opacity-0 translate-y-1 scale-95"
            >
              <Menu.Items className="absolute right-0 mt-2 w-[min(20rem,calc(100vw-1.5rem))] overflow-hidden rounded-xl border border-line bg-surface shadow-e4 focus:outline-none">
                <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
                  <h2 className="font-semibold text-ink-900">Notifications</h2>
                  <span className="rounded-full bg-brand-50 px-2.5 py-1 text-caption font-semibold text-brand-800">
                    {unread > 0 ? `${unread} unread` : 'All caught up'}
                  </span>
                </div>

                <div className="max-h-80 overflow-y-auto">
                  {notificationsLoading && (
                    <p className="px-4 py-6 text-center text-sm text-ink-500">Loading notifications…</p>
                  )}

                  {!notificationsLoading && notifications.length === 0 && (
                    <p className="px-4 py-8 text-center text-sm text-ink-500">
                      Nothing needs your attention right now.
                    </p>
                  )}

                  {!notificationsLoading && notifications.map((notification) => (
                    <Menu.Item key={notification.id}>
                      {({ active }) => (
                        <Link
                          to={notification.complaint_id ? `${isAdmin() ? '/admin' : '/student'}/complaints/${notification.complaint_id}` : notificationPath}
                          className={cn(
                            'block border-b border-line px-4 py-3 transition-colors last:border-0',
                            active && 'bg-canvas',
                          )}
                        >
                          <div className="flex gap-3">
                            <span
                              className={cn(
                                'mt-1 h-2 w-2 flex-none rounded-full',
                                notification.is_read ? 'bg-line' : 'bg-brand-700',
                              )}
                              aria-hidden="true"
                            />
                            <div className="min-w-0 flex-1">
                              <p className="line-clamp-1 text-sm font-semibold text-ink-900">
                                {notification.title}
                              </p>
                              <p className="mt-0.5 line-clamp-2 text-caption text-ink-600">
                                {notification.message}
                              </p>
                              <p className="mt-1 text-caption text-ink-500">
                                {formatRelative(notification.created_at)}
                              </p>
                            </div>
                          </div>
                        </Link>
                      )}
                    </Menu.Item>
                  ))}
                </div>

                <div className="border-t border-line bg-canvas p-2">
                  <Link
                    to={notificationPath}
                    className="block min-h-touch rounded-md px-3 py-2.5 text-center text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-50"
                  >
                    View all notifications
                  </Link>
                </div>
              </Menu.Items>
            </Transition>
          </Menu>

          <Menu as="div" className="relative">
            <Menu.Button className="inline-flex min-h-touch items-center gap-2 rounded-md p-1.5 pr-1 sm:pr-2.5 transition-colors hover:bg-canvas">
              <Avatar name={user?.full_name} size="sm" />
              <div className="hidden min-w-0 text-left sm:block">
                <p className="max-w-28 truncate text-sm font-semibold leading-none text-ink-900">
                  {user?.full_name?.split(' ')[0] || 'User'}
                </p>
                <p className="mt-0.5 truncate text-caption text-ink-500">
                  {ROLE_LABELS[user?.role] || 'Student'}
                </p>
              </div>
            </Menu.Button>

            <Transition
              as={Fragment}
              enter="transition ease-out duration-150"
              enterFrom="opacity-0 translate-y-1 scale-95"
              enterTo="opacity-100 translate-y-0 scale-100"
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100 translate-y-0 scale-100"
              leaveTo="opacity-0 translate-y-1 scale-95"
            >
              <Menu.Items className="absolute right-0 mt-2 w-[min(14rem,calc(100vw-1.5rem))] overflow-hidden rounded-xl border border-line bg-surface shadow-e4 focus:outline-none">
                <div className="border-b border-line px-4 py-3">
                  <p className="truncate font-semibold text-ink-900">{user?.full_name}</p>
                  <p className="truncate text-sm text-ink-500">{user?.email}</p>
                </div>

                <div className="p-2">
                  <Menu.Item>
                    {({ active }) => (
                      <Link
                        to={profilePath}
                        className={cn(
                          'flex min-h-touch items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors',
                          active ? 'bg-canvas text-ink-900' : 'text-ink-600',
                        )}
                      >
                        <UserCircleIcon className="h-5 w-5" aria-hidden="true" />
                        <span>My profile</span>
                      </Link>
                    )}
                  </Menu.Item>

                  <Menu.Item>
                    {({ active }) => (
                      <Link
                        to={profilePath}
                        className={cn(
                          'flex min-h-touch items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors',
                          active ? 'bg-canvas text-ink-900' : 'text-ink-600',
                        )}
                      >
                        <Cog6ToothIcon className="h-5 w-5" aria-hidden="true" />
                        <span>Settings</span>
                      </Link>
                    )}
                  </Menu.Item>

                  <div className="my-2 h-px bg-line" />

                  <Menu.Item>
                    {({ active }) => (
                      <button
                        type="button"
                        onClick={handleLogout}
                        className={cn(
                          'flex min-h-touch w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors',
                          active ? 'bg-[#FEF2F2] text-[#B91C1C]' : 'text-ink-600',
                        )}
                      >
                        <ArrowRightOnRectangleIcon className="h-5 w-5" aria-hidden="true" />
                        <span>Log out</span>
                      </button>
                    )}
                  </Menu.Item>
                </div>
              </Menu.Items>
            </Transition>
          </Menu>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
