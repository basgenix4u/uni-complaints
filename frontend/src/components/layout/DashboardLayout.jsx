import React, { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from './Sidebar';
import BottomNav from './BottomNav';
import Navbar from './Navbar';
import VerificationBanner from '../shared/VerificationBanner';
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
  const { isAdmin, user } = useAuthStore();
  const isStudent = user?.role === 'student';

  const pageTitle = getPageTitle(location.pathname, isAdmin());

  // A navigation click can change the route before the drawer's own click
  // handler runs (for example when a link is activated by the keyboard).
  // Closing from the route change as well makes the mobile overlay
  // impossible to strand over the next page.
  useEffect(() => {
    // This is an intentional UI reset: route changes must dismiss the
    // mobile drawer even when navigation came from the keyboard or history.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSidebarOpen(false);
  }, [location.pathname]);

  // Keep the page from scrolling underneath an open drawer, and always
  // restore the body's state when the drawer closes or the component
  // unmounts. The previous implementation left a locked page behind on
  // some mobile browsers after the overlay had visually disappeared.
  useEffect(() => {
    if (!sidebarOpen) {
      document.body.style.overflow = '';
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [sidebarOpen]);

  // If a phone is rotated or resized to desktop while the drawer is open,
  // close it so the hidden mobile layer cannot keep intercepting input.
  useEffect(() => {
    const media = window.matchMedia('(min-width: 1024px)');
    const closeOnDesktop = (event) => {
      if (event.matches) setSidebarOpen(false);
    };

    closeOnDesktop(media);
    media.addEventListener?.('change', closeOnDesktop);
    return () => media.removeEventListener?.('change', closeOnDesktop);
  }, []);

  return (
    <div className="min-h-screen min-w-0 overflow-x-clip bg-canvas">
      {/* Desktop Sidebar */}
      <Sidebar isOpen={true} onClose={() => {}} isMobile={false} />

      {/* Mobile Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isMobile={true}
      />

      {/* Main Content */}
      <div className="min-w-0 lg:pl-64">
        {/* Navbar */}
        <Navbar
          isMenuOpen={sidebarOpen}
          onMenuClick={() => setSidebarOpen((open) => !open)}
          title={pageTitle}
        />

        <VerificationBanner />

        {/* Page Content. Bottom padding on phones clears the tab bar. */}
        <main
          className={`mx-auto min-w-0 max-w-[1680px] px-3 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8 ${
            isStudent ? 'pb-[calc(5rem+env(safe-area-inset-bottom))] lg:pb-8' : ''
          }`}
        >
          <motion.div
            className="min-w-0"
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

      {/* Students are phone-first; the four destinations that matter sit
          in thumb reach instead of behind the hamburger. Staff keep the
          sidebar — triage is desk work. */}
      {isStudent && <BottomNav />}
    </div>
  );
};

export default DashboardLayout;