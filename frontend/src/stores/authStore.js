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
          const response = await authService.login(credentials);
          const { user, access_token, refresh_token } = response.data;
          
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
          return { success: false, error: errorMessage };
        }
      },

      register: async (data) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await authService.register(data);
          const { user, access_token, refresh_token } = response.data;
          
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
          const errorMessage = err.response?.data?.message || 'Registration failed';
          set({ isLoading: false, error: errorMessage });
          return { success: false, error: errorMessage };
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
          const response = await authService.getMe();
          const { user } = response.data;
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
          const response = await authService.updateProfile(data);
          const { user } = response.data;
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

      isAdmin: () => {
        const { user } = get();
        return user?.role === 'admin' || user?.role === 'super_admin';
      },

      isSuperAdmin: () => {
        const { user } = get();
        return user?.role === 'super_admin';
      },

      initializeAuth: async () => {
        const accessToken = localStorage.getItem('access_token');
        
        if (accessToken) {
          set({ accessToken, isLoading: true });
          
          try {
            const response = await authService.getMe();
            const { user } = response.data;
            
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