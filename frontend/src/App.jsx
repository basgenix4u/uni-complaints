import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AnimatePresence } from 'framer-motion';

// Layouts
import { AuthLayout, DashboardLayout } from './components/layout';

// Auth Pages
import { LoginPage, RegisterPage } from './pages/auth';

// Student Pages
import {
  StudentDashboard,
  MyComplaints,
  NewComplaint,
  ComplaintDetails,
  StudentNotifications,
  StudentProfile,
} from './pages/student';

// Admin Pages
import {
  AdminDashboard,
  AdminComplaints,
  AdminComplaintDetails,
  AdminAnalytics,
  AdminUsers,
  AdminSettings,
} from './pages/admin';

// Shared
import { ProtectedRoute } from './components/shared';
import useAuthStore from './stores/authStore';

// Create Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
    },
  },
});

// Home Redirect Component
const HomeRedirect = () => {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role === 'student') {
    return <Navigate to="/student/dashboard" replace />;
  }

  return <Navigate to="/admin/dashboard" replace />;
};

function App() {
  const { initializeAuth } = useAuthStore();

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AnimatePresence mode="wait">
          <Routes>
            {/* Home Redirect */}
            <Route path="/" element={<HomeRedirect />} />

            {/* Auth Routes */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>

            {/* Student Routes */}
            <Route
              element={
                <ProtectedRoute allowedRoles={['student']}>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/student/dashboard" element={<StudentDashboard />} />
              <Route path="/student/complaints" element={<MyComplaints />} />
              <Route path="/student/complaints/new" element={<NewComplaint />} />
              <Route path="/student/complaints/:id" element={<ComplaintDetails />} />
              <Route path="/student/notifications" element={<StudentNotifications />} />
              <Route path="/student/profile" element={<StudentProfile />} />
            </Route>

            {/* Admin Routes */}
            <Route
              element={
                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/complaints" element={<AdminComplaints />} />
              <Route path="/admin/complaints/:id" element={<AdminComplaintDetails />} />
              <Route path="/admin/analytics" element={<AdminAnalytics />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/settings" element={<AdminSettings />} />
            </Route>

            {/* 404 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AnimatePresence>
      </BrowserRouter>

      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#fff',
            color: '#171717',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.08)',
            borderRadius: '1rem',
            border: '1px solid #f5f5f5',
            padding: '1rem',
          },
          success: {
            iconTheme: { primary: '#22c55e', secondary: '#fff' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#fff' },
          },
        }}
      />
    </QueryClientProvider>
  );
}

export default App;