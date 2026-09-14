import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import useAuthStore from '../../stores/authStore';

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

const getPageTitle = (pathname, isAdmin) => {
  const titles = {
    // Student routes
    '/student/dashboard': 'Dashboard',
    '/student/complaints': 'My Complaints',
    '/student/complaints/new': 'Submit Complaint',
    '/student/notifications': 'Notifications',
    '/student/profile': 'My Profile',
    // Admin routes
    '/admin/dashboard': 'Dashboard',
    '/admin/complaints': 'All Complaints',
    '/admin/analytics': 'Analytics',
    '/admin/users': 'User Management',
    '/admin/settings': 'Settings',
  };

  // Check for dynamic routes
  if (pathname.startsWith('/student/complaints/') && pathname !== '/student/complaints/new') {
    return 'Complaint Details';
  }
  if (pathname.startsWith('/admin/complaints/')) {
    return 'Complaint Details';
  }
  if (pathname.startsWith('/admin/users/')) {
    return 'User Details';
  }

  return titles[pathname] || 'Dashboard';
};

const DashboardLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const { isAdmin } = useAuthStore();

  const pageTitle = getPageTitle(location.pathname, isAdmin());

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Desktop Sidebar */}
      <Sidebar isOpen={true} onClose={() => {}} isMobile={false} />

      {/* Mobile Sidebar */}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
        isMobile={true} 
      />

      {/* Main Content */}
      <div className="lg:pl-72">
        {/* Navbar */}
        <Navbar 
          onMenuClick={() => setSidebarOpen(true)} 
          title={pageTitle}
        />

        {/* Page Content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <motion.div
            key={location.pathname}
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;