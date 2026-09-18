import React, { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

// Layouts
import { AuthLayout, DashboardLayout } from './components/layout';

// Route components are loaded on demand: a student signing in should not
// download the admin analytics bundle.
const LoginPage = lazy(() => import('./pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'));
const TrackPage = lazy(() => import('./pages/public/TrackPage'));
const ForgotPasswordPage = lazy(() => import('./pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./pages/auth/ResetPasswordPage'));

const StudentDashboard = lazy(() => import('./pages/student/StudentDashboard'));
const MyComplaints = lazy(() => import('./pages/student/MyComplaints'));
const NewComplaint = lazy(() => import('./pages/student/NewComplaint'));
const ComplaintDetails = lazy(() => import('./pages/student/ComplaintDetails'));
const StudentNotifications = lazy(() => import('./pages/student/StudentNotifications'));
const StudentProfile = lazy(() => import('./pages/student/StudentProfile'));

const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const AdminComplaints = lazy(() => import('./pages/admin/AdminComplaints'));
const AdminComplaintDetails = lazy(() => import('./pages/admin/AdminComplaintDetails'));
const AdminAnalytics = lazy(() => import('./pages/admin/AdminAnalytics'));
const AdminUsers = lazy(() => import('./pages/admin/AdminUsers'));
const AdminSettings = lazy(() => import('./pages/admin/AdminSettings'));
const InstitutionSettings = lazy(() => import('./pages/admin/InstitutionSettings'));
const PlatformInstitutions = lazy(() => import('./pages/platform/PlatformInstitutions'));

// Shared
import { CommandPalette, ProtectedRoute } from './components/shared';
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

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas" role="status" aria-label="Loading">
      <span className="h-8 w-8 animate-spin rounded-full border-2 border-brand-700 border-t-transparent" />
    </div>
  );
}

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
        <CommandPalette />
          <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/track" element={<TrackPage />} />
            {/* Home Redirect */}
            <Route path="/" element={<HomeRedirect />} />

            {/* Auth Routes */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />
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
                <ProtectedRoute allowedRoles={['officer', 'dept_head', 'institution_admin', 'platform_admin']}>
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
              <Route path="/admin/notifications" element={<StudentNotifications />} />
            </Route>

            {/* Institution administration */}
            <Route
              element={
                <ProtectedRoute allowedRoles={['institution_admin', 'platform_admin']}>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/admin/institution" element={<InstitutionSettings />} />
            </Route>

            {/* Platform owner */}
            <Route
              element={
                <ProtectedRoute allowedRoles={['platform_admin']}>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/platform/institutions" element={<PlatformInstitutions />} />
            </Route>

            {/* 404 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
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