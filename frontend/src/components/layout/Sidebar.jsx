import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
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
  ClipboardDocumentListIcon,
  ArrowRightOnRectangleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '../../utils/cn';
import useAuthStore from '../../stores/authStore';

const Sidebar = ({ isOpen, onClose, isMobile = false }) => {
  const location = useLocation();
  const { user, logout, isAdmin } = useAuthStore();

  const studentNavItems = [
    { name: 'Dashboard', href: '/student/dashboard', icon: HomeIcon },
    { name: 'My Complaints', href: '/student/complaints', icon: DocumentTextIcon },
    { name: 'Submit Complaint', href: '/student/complaints/new', icon: PlusCircleIcon },
    { name: 'Notifications', href: '/student/notifications', icon: BellIcon },
    { name: 'Profile', href: '/student/profile', icon: UserIcon },
  ];

  const adminNavItems = [
    { name: 'Dashboard', href: '/admin/dashboard', icon: HomeIcon },
    { name: 'All Complaints', href: '/admin/complaints', icon: ClipboardDocumentListIcon },
    { name: 'Analytics', href: '/admin/analytics', icon: ChartBarIcon },
    { name: 'Users', href: '/admin/users', icon: UsersIcon, superAdminOnly: true },
    { name: 'Settings', href: '/admin/settings', icon: Cog6ToothIcon },
  ];

  const navItems = isAdmin() ? adminNavItems : studentNavItems;
  const userRole = user?.role === 'super_admin' ? 'Super Admin' : user?.role === 'admin' ? 'Admin' : 'Student';

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  const sidebarContent = (
    <>
      {/* Logo Section */}
      <div className="flex items-center justify-between h-16 px-6 border-b border-neutral-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/30">
            <span className="text-white font-bold text-lg">U</span>
          </div>
          <div>
            <h1 className="font-bold text-neutral-900 text-lg leading-none">UniComplaint</h1>
            <p className="text-xs text-neutral-500">Management System</p>
          </div>
        </div>
        
        {isMobile && (
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-neutral-100 transition-colors lg:hidden"
          >
            <XMarkIcon className="w-5 h-5 text-neutral-500" />
          </button>
        )}
      </div>

      {/* User Info */}
      <div className="p-4 mx-4 mt-4 rounded-xl bg-gradient-to-br from-primary-50 to-primary-100/50 border border-primary-100">
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
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        <p className="px-3 mb-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">
          Menu
        </p>
        
        {navItems.map((item) => {
          // Skip super admin only items for regular admins
          if (item.superAdminOnly && user?.role !== 'super_admin') {
            return null;
          }

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
                'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative',
                isActive
                  ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30'
                  : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute inset-0 bg-primary-500 rounded-xl -z-10"
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
              <item.icon className={cn('w-5 h-5 flex-shrink-0', isActive ? 'text-white' : 'text-neutral-400 group-hover:text-neutral-600')} />
              <span className="font-medium">{item.name}</span>
              
              {item.name === 'Notifications' && (
                <span className="ml-auto w-5 h-5 rounded-full bg-danger-500 text-white text-xs flex items-center justify-center font-semibold">
                  3
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Logout Button */}
      <div className="p-4 border-t border-neutral-100">
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
              className="fixed left-0 top-0 h-full w-72 bg-white shadow-soft-xl z-50 flex flex-col lg:hidden"
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
    <aside className="hidden lg:flex lg:flex-col lg:w-72 lg:fixed lg:inset-y-0 bg-white border-r border-neutral-100 shadow-soft">
      {sidebarContent}
    </aside>
  );
};

export default Sidebar;