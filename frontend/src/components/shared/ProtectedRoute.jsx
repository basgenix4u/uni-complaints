import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import useAuthStore from '../../stores/authStore';
import { Spinner } from '../ui';

const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const location = useLocation();
  const { user, isAuthenticated, isLoading, initializeAuth } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated && !isLoading) {
      initializeAuth();
    }
  }, [isAuthenticated, isLoading, initializeAuth]);

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <Spinner size="xl" className="mx-auto mb-4" />
          <p className="text-neutral-500">Loading...</p>
        </motion.div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  if (allowedRoles.length > 0 && !allowedRoles.includes(user?.role)) {
    // Redirect to appropriate dashboard based on role
    if (user?.role === 'student') {
      return <Navigate to="/student/dashboard" replace />;
    } else {
      return <Navigate to="/admin/dashboard" replace />;
    }
  }

  return children;
};

export default ProtectedRoute;