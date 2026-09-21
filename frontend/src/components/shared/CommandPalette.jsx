import { Fragment, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Combobox, Dialog, Transition } from '@headlessui/react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowRightIcon,
  ArrowsRightLeftIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  HomeIcon,
  MagnifyingGlassIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';

import StatusBadge from '../ui/StatusBadge';
import { complaintService } from '../../services/api';
import useAuthStore from '../../stores/authStore';

/**
 * Keyboard launcher, opened with Control or Command and K.
 *
 * Someone working a queue of several hundred complaints spends more time
 * navigating than reading. Jumping straight to a ticket by number removes
 * the list, the filter and the scroll.
 */

const STAFF_ROLES = ['officer', 'dept_head', 'dean', 'institution_admin', 'platform_admin'];

const DESTINATIONS = [
  { name: 'Dashboard', to: '/admin/dashboard', icon: HomeIcon, roles: STAFF_ROLES },
  { name: 'Complaints', to: '/admin/complaints', icon: ClipboardDocumentListIcon, roles: STAFF_ROLES },
  { name: 'Unassigned complaints', to: '/admin/complaints?view=unassigned', icon: ClipboardDocumentListIcon, roles: STAFF_ROLES },
  { name: 'Analytics', to: '/admin/analytics', icon: ChartBarIcon, roles: STAFF_ROLES },
  { name: 'People', to: '/admin/users', icon: UsersIcon, roles: ['institution_admin', 'platform_admin'] },
  { name: 'Institution settings', to: '/admin/institution', icon: HomeIcon, roles: ['institution_admin', 'platform_admin'] },
  { name: 'Routing: who answers what', to: '/admin/routing', icon: ArrowsRightLeftIcon, roles: ['institution_admin', 'platform_admin'] },
  { name: 'Still waiting: ignored complaints', to: '/admin/ignored', icon: ExclamationTriangleIcon, roles: ['institution_admin', 'platform_admin'] },
  { name: 'Institutions', to: '/platform/institutions', icon: HomeIcon, roles: ['platform_admin'] },
  { name: 'My complaints', to: '/student/complaints', icon: DocumentTextIcon, roles: ['student'] },
  { name: 'File a complaint', to: '/student/complaints/new', icon: DocumentTextIcon, roles: ['student'] },
  { name: 'My dashboard', to: '/student/dashboard', icon: HomeIcon, roles: ['student'] },
];

export default function CommandPalette() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuthStore();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((current) => !current);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const isStaff = STAFF_ROLES.includes(user?.role);

  // Only searched once there is enough to be worth a request, and the
  // result is cached briefly so repeated opens are instant.
  const { data } = useQuery({
    queryKey: ['palette-search', query],
    queryFn: () => complaintService.list({ search: query, per_page: 6 }),
    enabled: open && query.trim().length >= 2,
    staleTime: 30_000,
  });

  const destinations = useMemo(
    () =>
      DESTINATIONS.filter((item) => item.roles.includes(user?.role)).filter((item) =>
        item.name.toLowerCase().includes(query.trim().toLowerCase()),
      ),
    [query, user?.role],
  );

  const complaints = data?.complaints || [];

  const go = (item) => {
    setOpen(false);
    setQuery('');
    if (item.to) {
      navigate(item.to);
      return;
    }
    navigate(isStaff ? `/admin/complaints/${item.id}` : `/student/complaints/${item.id}`);
  };

  if (!isAuthenticated) return null;

  return (
    <Transition show={open} as={Fragment} afterLeave={() => setQuery('')}>
      <Dialog onClose={setOpen} className="relative z-50">
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto p-4 pt-[15vh]">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-200"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="mx-auto max-w-xl overflow-hidden rounded-xl border border-line bg-surface shadow-e4">
              <Combobox onChange={go}>
                <div className="flex items-center gap-3 border-b border-line px-4">
                  <MagnifyingGlassIcon className="h-5 w-5 flex-none text-ink-500" aria-hidden="true" />
                  <Combobox.Input
                    autoFocus
                    className="h-14 w-full border-0 bg-transparent text-base text-ink-900 placeholder:text-ink-500 focus:outline-none"
                    placeholder="Search a ticket number, or jump to a page"
                    onChange={(event) => setQuery(event.target.value)}
                  />
                  <kbd className="hidden flex-none rounded border border-line px-1.5 py-0.5 font-mono text-caption text-ink-500 sm:block">
                    esc
                  </kbd>
                </div>

                <Combobox.Options static className="max-h-80 overflow-y-auto py-2">
                  {complaints.length > 0 && (
                    <Section title="Complaints">
                      {complaints.map((complaint) => (
                        <Combobox.Option key={complaint.id} value={complaint} as={Fragment}>
                          {({ active }) => (
                            <li className={row(active)}>
                              <span className="font-mono text-caption text-ink-500">
                                {complaint.ticket_number}
                              </span>
                              <span className="min-w-0 flex-1 truncate text-ink-900">
                                {complaint.title}
                              </span>
                              <StatusBadge
                                status={complaint.status}
                                overdue={complaint.is_overdue}
                                size="sm"
                              />
                            </li>
                          )}
                        </Combobox.Option>
                      ))}
                    </Section>
                  )}

                  {destinations.length > 0 && (
                    <Section title="Go to">
                      {destinations.map((item) => (
                        <Combobox.Option key={item.to} value={item} as={Fragment}>
                          {({ active }) => (
                            <li className={row(active)}>
                              <item.icon className="h-5 w-5 flex-none text-ink-500" aria-hidden="true" />
                              <span className="flex-1 text-ink-900">{item.name}</span>
                              <ArrowRightIcon className="h-4 w-4 flex-none text-ink-500" aria-hidden="true" />
                            </li>
                          )}
                        </Combobox.Option>
                      ))}
                    </Section>
                  )}

                  {destinations.length === 0 && complaints.length === 0 && (
                    <p className="px-4 py-8 text-center text-sm text-ink-500">
                      {query.trim().length >= 2
                        ? 'Nothing matches that.'
                        : 'Type a ticket number or a page name.'}
                    </p>
                  )}
                </Combobox.Options>
              </Combobox>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}

const row = (active) =>
  `flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm ${
    active ? 'bg-brand-50 text-brand-900' : ''
  }`;

function Section({ title, children }) {
  return (
    <>
      <p className="px-4 pb-1 pt-2 text-caption font-bold uppercase tracking-wider text-ink-500">
        {title}
      </p>
      <ul>{children}</ul>
    </>
  );
}
