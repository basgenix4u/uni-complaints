import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { authService } from '../services/api';

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),

      login: async (credentials) => {
        set({ isLoading: true, error: null });
        
        try {
          const { user, access_token, refresh_token } = await authService.login(credentials);
          
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
          
          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          
          return { success: true, user };
        } catch (err) {
          const errorMessage = err.response?.data?.message || 'Login failed';
          set({ isLoading: false, error: errorMessage });
          // The caller gets the raw error too: the 429 handler needs the
          // Retry-After header, which the message alone cannot carry.
          return { success: false, error: errorMessage, raw: err };
        }
      },

      register: async (data) => {
        set({ isLoading: true, error: null });
        
        try {
          const { user, access_token, refresh_token } = await authService.register(data);
          
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
          
          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          
          return { success: true, user };
        } catch (err) {
          const message = err.response?.data?.message || 'Registration failed';
          set({ isLoading: false, error: message });
          // Field errors are passed through so the form can mark the
          // offending input rather than only showing a toast.
          return { success: false, error: message, errors: err.response?.data?.errors || {} };
        }
      },

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshUser: async () => {
        try {
          const { user } = await authService.me();
          set({ user });
          return { success: true, user };
        } catch (_err) {
          get().logout();
          return { success: false };
        }
      },

      updateProfile: async (data) => {
        set({ isLoading: true, error: null });
        
        try {
          const { user } = await authService.updateProfile(data);
          set({ user, isLoading: false });
          return { success: true, user };
        } catch (err) {
          const errorMessage = err.response?.data?.message || 'Update failed';
          set({ isLoading: false, error: errorMessage });
          return { success: false, error: errorMessage };
        }
      },

      changePassword: async (data) => {
        set({ isLoading: true, error: null });
        
        try {
          await authService.changePassword(data);
          set({ isLoading: false });
          return { success: true };
        } catch (err) {
          const errorMessage = err.response?.data?.message || 'Password change failed';
          set({ isLoading: false, error: errorMessage });
          return { success: false, error: errorMessage };
        }
      },

      // Roles, most privileged last. Kept in one place so a check cannot
      // drift from the hierarchy the server enforces.
      isStaff: () => {
        const { user } = get();
        return ['officer', 'dept_head', 'institution_admin', 'platform_admin'].includes(user?.role);
      },

      isAdmin: () => {
        const { user } = get();
        return ['officer', 'dept_head', 'institution_admin', 'platform_admin'].includes(user?.role);
      },

      isInstitutionAdmin: () => {
        const { user } = get();
        return ['institution_admin', 'platform_admin'].includes(user?.role);
      },

      isPlatformAdmin: () => get().user?.role === 'platform_admin',

      initializeAuth: async () => {
        const accessToken = localStorage.getItem('access_token');
        
        if (accessToken) {
          set({ accessToken, isLoading: true });
          
          try {
            const { user } = await authService.me();

            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            });
          } catch (_err) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            
            set({
              user: null,
              accessToken: null,
              refreshToken: null,
              isAuthenticated: false,
              isLoading: false,
            });
          }
        } else {
          set({ isLoading: false });
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;