import React, { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HomeIcon,
  DocumentTextIcon,
  PlusCircleIcon,
  BellIcon,
  UserIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  UsersIcon,
  BuildingOffice2Icon,
  BuildingLibraryIcon,
  ArrowsRightLeftIcon,
  ExclamationTriangleIcon,
  UserPlusIcon,
  AcademicCapIcon,
  EnvelopeIcon,
  ShieldCheckIcon,
  ClipboardDocumentListIcon,
  ArrowRightOnRectangleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '../../utils/cn';
import { notificationService } from '../../services/api';
import useAuthStore from '../../stores/authStore';

const Sidebar = ({ isOpen, onClose, isMobile = false }) => {
  const location = useLocation();
  const { user, logout, isAdmin } = useAuthStore();

  const { data: notificationData } = useQuery({
    queryKey: ['nav-unread-count', user?.id],
    queryFn: () => notificationService.unreadCount(),
    enabled: Boolean(user),
    staleTime: 30_000,
  });
  const unreadCount = notificationData?.unread_count || 0;

  useEffect(() => {
    if (!isMobile || !isOpen) return undefined;

    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [isMobile, isOpen, onClose]);

  const studentNavItems = [
    { name: 'Dashboard', href: '/student/dashboard', icon: HomeIcon },
    { name: 'My Complaints', href: '/student/complaints', icon: DocumentTextIcon },
    { name: 'Submit Complaint', href: '/student/complaints/new', icon: PlusCircleIcon },
    { name: 'Notifications', href: '/student/notifications', icon: BellIcon },
    { name: 'Profile', href: '/student/profile', icon: UserIcon },
    { name: 'Your data', href: '/student/privacy', icon: ShieldCheckIcon },
  ];

  // Entries are filtered by role rather than hidden by CSS, so a link is
  // never shown to someone the server would refuse.
  const adminNavItems = [
    { name: 'Dashboard', href: '/admin/dashboard', icon: HomeIcon },
    { name: 'Complaints', href: '/admin/complaints', icon: ClipboardDocumentListIcon },
    { name: 'Notifications', href: '/admin/notifications', icon: BellIcon },
    { name: 'Analytics', href: '/admin/analytics', icon: ChartBarIcon },
    { name: 'People', href: '/admin/users', icon: UsersIcon, roles: ['institution_admin', 'platform_admin'] },
    { name: 'Invite staff', href: '/admin/invitations', icon: EnvelopeIcon, roles: ['dept_head', 'dean', 'institution_admin', 'platform_admin'] },
    { name: 'Institution', href: '/admin/institution', icon: BuildingOffice2Icon, roles: ['institution_admin', 'platform_admin'], needsInstitution: true },
    { name: 'Routing', href: '/admin/routing', icon: ArrowsRightLeftIcon, roles: ['institution_admin', 'platform_admin'], needsInstitution: true },
    { name: 'Still waiting', href: '/admin/ignored', icon: ExclamationTriangleIcon, roles: ['institution_admin', 'platform_admin'] },
    { name: 'Registrations', href: '/admin/registrations', icon: UserPlusIcon, roles: ['institution_admin', 'platform_admin'] },
    { name: 'Academic structure', href: '/admin/academic', icon: AcademicCapIcon, roles: ['institution_admin', 'platform_admin'] },
    { name: 'Institutions', href: '/platform/institutions', icon: BuildingLibraryIcon, roles: ['platform_admin'] },
    { name: 'My profile', href: '/admin/settings', icon: Cog6ToothIcon },
    { name: 'Your data', href: '/admin/privacy', icon: ShieldCheckIcon },
  ];

  const ROLE_LABELS = {
    student: 'Student',
    officer: 'Officer',
    dept_head: 'Department head',
    dean: 'Dean',
    institution_admin: 'Administrator',
    platform_admin: 'Platform owner',
  };

  // Some pages administer a single institution, and the platform owner
  // belongs to none. Their role permits the route, so role alone is not
  // enough: the request 404s and the page has nothing to show.
  const navItems = (isAdmin() ? adminNavItems : studentNavItems).filter(
    (item) =>
      (!item.roles || item.roles.includes(user?.role)) &&
      (!item.needsInstitution || Boolean(user?.institution_id)),
  );
  const userRole = ROLE_LABELS[user?.role] || 'Student';

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  const sidebarContent = (
    <>
      {/* Logo Section */}
      <div className="flex h-16 items-center justify-between border-b border-line px-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/30">
            <span className="text-white font-bold text-lg">U</span>
          </div>
          <div>
            <h1 className="font-bold text-neutral-900 text-lg leading-none">Resolve</h1>
            <p className="text-xs text-neutral-500">Complaint resolution</p>
          </div>
        </div>
        
        {isMobile && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation menu"
            className="inline-flex min-h-touch min-w-touch items-center justify-center rounded-md hover:bg-canvas transition-colors lg:hidden"
          >
            <XMarkIcon className="w-5 h-5 text-neutral-500" />
          </button>
        )}
      </div>

      {/* User Info */}
      <div className="mx-3 mt-3 rounded-md border border-brand-200 bg-brand-50 p-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white font-semibold text-lg shadow-lg">
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-neutral-900 truncate">{user?.full_name || 'User'}</p>
            <p className="text-xs text-primary-600 font-medium">{userRole}</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <p className="px-3 mb-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">
          Menu
        </p>
        
        {navItems.map((item) => {
          // Skip super admin only items for regular admins


          const isActive = location.pathname === item.href || 
                          (item.href !== '/student/dashboard' && 
                           item.href !== '/admin/dashboard' && 
                           location.pathname.startsWith(item.href));

          return (
            <NavLink
              key={item.name}
              to={item.href}
              onClick={isMobile ? onClose : undefined}
              className={cn(
                'flex min-h-touch items-center gap-3 rounded-md px-3 py-2.5 transition-all duration-200 group relative',
                isActive
                  ? 'bg-brand-700 text-white shadow-e1'
                  : 'text-ink-600 hover:bg-canvas hover:text-ink-900'
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute inset-0 -z-10 rounded-md bg-brand-700"
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
              <item.icon className={cn('w-5 h-5 flex-shrink-0', isActive ? 'text-white' : 'text-neutral-400 group-hover:text-neutral-600')} />
              <span className="font-medium">{item.name}</span>
              
              {item.name === 'Notifications' && unreadCount > 0 && (
                <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-[#B91C1C] px-1 text-xs font-semibold text-white">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Logout Button */}
      <div className="border-t border-line p-3">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-neutral-600 hover:bg-danger-50 hover:text-danger-600 transition-all duration-200 group"
        >
          <ArrowRightOnRectangleIcon className="w-5 h-5 text-neutral-400 group-hover:text-danger-500" />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </>
  );

  // Mobile Sidebar with Overlay
  if (isMobile) {
    return (
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            />
            
            {/* Sidebar */}
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              id="mobile-navigation"
              role="dialog"
              aria-modal="true"
              aria-label="Mobile navigation"
              className="fixed left-0 top-0 z-50 flex h-full w-[min(18rem,calc(100vw-1rem))] flex-col bg-surface shadow-e4 lg:hidden"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    );
  }

  // Desktop Sidebar
  return (
    <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-line bg-surface shadow-e1 lg:flex">
      {sidebarContent}
    </aside>
  );
};

export default Sidebar;