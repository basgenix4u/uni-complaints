import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  ArrowRightEndOnRectangleIcon,
  EnvelopeIcon,
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
} from '@heroicons/react/24/outline';
import { Button, Input } from '../../components/ui';
import useAuthStore from '../../stores/authStore';
import useCapsLock from '../../hooks/useCapsLock';
import useRetryAfter from '../../hooks/useRetryAfter';
import useSlowRequest from '../../hooks/useSlowRequest';

// Validation Schema
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(6, 'Password must be at least 6 characters'),
});

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, capsLockProps] = useCapsLock();
  const retry = useRetryAfter();
  // The free tier sleeps; the first request of the day takes up to a
  // minute. Without narration that minute looks like a broken site.
  const slowMessage = useSlowRequest(isLoading);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = async (data) => {
    try {
      const result = await login(data);
      
      if (result.success) {
        toast.success('Welcome back!');
        
        // Redirect based on role
        if (result.user.role === 'student') {
          navigate('/student/dashboard');
        } else {
          navigate('/admin/dashboard');
        }
      } else {
        // A 429 carries how long to wait. Counting it down beats a
        // toast that invites the retry the limit exists to stop.
        if (result.raw?.response?.status === 429 && retry.start(result.raw)) return;
        toast.error(result.error || 'Login failed');
      }
    } catch (error) {
      console.error("Login error:", error);
      toast.error("An unexpected error occurred");
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-display text-3xl font-bold tracking-tight text-ink-900"
        >
          Welcome back
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-1 text-ink-600"
        >
          Sign in to your account to continue
        </motion.p>
      </div>

      {/* Form */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5"
      >
        {/* Email. autocomplete and inputmode so password managers fill
            it and phone keyboards show the @ key. */}
        <Input
          label="Email Address"
          type="email"
          placeholder="Enter your email"
          autoComplete="email"
          inputMode="email"
          leftIcon={<EnvelopeIcon className="h-5 w-5" />}
          error={errors.email?.message}
          {...register('email')}
        />

        {/* Password */}
        <Input
          label="Password"
          type={showPassword ? 'text' : 'password'}
          placeholder="Enter your password"
          autoComplete="current-password"
          leftIcon={<LockClosedIcon className="h-5 w-5" />}
          error={errors.password?.message}
          hint={capsLock ? 'Caps lock is on.' : undefined}
          {...capsLockProps}
          rightSlot={
            <button
              type="button"
              onClick={() => setShowPassword((shown) => !shown)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="flex h-9 w-9 items-center justify-center rounded-md text-ink-500 transition-colors hover:text-ink-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
            >
              {showPassword ? (
                <EyeSlashIcon className="h-5 w-5" />
              ) : (
                <EyeIcon className="h-5 w-5" />
              )}
            </button>
          }
          {...register('password')}
        />

        {/* Forgot password */}
        <div className="flex items-center justify-end">
          <Link
            to="/forgot-password"
            className="text-sm font-medium text-brand-700 hover:text-brand-800"
          >
            Forgot password?
          </Link>
        </div>

        {/* Locked out: a clock that visibly runs down, in place of an
            error that invites trying again immediately. */}
        {retry.blocked && (
          <p
            role="alert"
            className="rounded-md px-4 py-3 text-sm font-medium"
            style={{
              backgroundColor: 'var(--status-progress-bg)',
              color: 'var(--status-progress-fg)',
            }}
          >
            Too many attempts. You can try again in {retry.label}.
          </p>
        )}

        {/* Submit Button */}
        <Button type="submit" size="lg" fullWidth loading={isLoading} disabled={retry.blocked}>
          <ArrowRightEndOnRectangleIcon className="h-5 w-5" aria-hidden="true" />
          Sign In
        </Button>

        {/* While the free-tier server wakes, say so; the alternative is
            a spinner indistinguishable from a hang. aria-live so the
            change is announced without stealing focus. */}
        <p aria-live="polite" className="min-h-5 text-center text-caption text-ink-500">
          {isLoading ? slowMessage : ''}
        </p>
      </motion.form>

      {/* Divider */}
      <div className="relative my-8">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-line" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-surface px-4 text-ink-500">or</span>
        </div>
      </div>

      {/* Register Link */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-8 text-center text-ink-600"
      >
        Don't have an account?{' '}
        <Link
          to="/register"
          className="font-semibold text-brand-700 hover:text-brand-800"
        >
          Create account
        </Link>
      </motion.p>
    </div>
  );
};

export default LoginPage;