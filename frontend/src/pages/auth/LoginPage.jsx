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
  LockClosedIcon,
} from '@heroicons/react/24/outline';
import { Button, Input } from '../../components/ui';
import Brand from '../../components/layout/Brand';
import useAuthStore from '../../stores/authStore';

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
        toast.error(result.error || 'Login failed');
      }
    } catch (error) {
      console.error("Login error:", error);
      toast.error("An unexpected error occurred");
    }
  };

  return (
    <div>
      {/* Header. The brand repeats here because on a wide screen the
          panel's copy sits far to the left; the form should stand on its
          own when it is all a narrow window shows. */}
      <div className="mb-8">
        <div className="mb-6 hidden items-center gap-3 lg:flex">
          <Brand className="h-11 w-11" />
          <span>
            <span className="block font-display text-xl font-bold text-brand-800">Resolve</span>
            <span className="block text-xs text-ink-500">Complaints that reach someone</span>
          </span>
        </div>
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-display text-3xl font-bold text-brand-800 mb-2"
        >
          Welcome back
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-neutral-500"
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
        {/* Email */}
        <Input
          label="Email Address"
          type="email"
          placeholder="Enter your email"
          leftIcon={<EnvelopeIcon className="w-5 h-5" />}
          error={errors.email?.message}
          {...register('email')}
        />

        {/* Password */}
        <Input
          label="Password"
          type="password"
          placeholder="Enter your password"
          leftIcon={<LockClosedIcon className="w-5 h-5" />}
          error={errors.password?.message}
          {...register('password')}
        />

        {/* Forgot password */}
        <div className="flex items-center justify-end">
          <Link
            to="/forgot-password"
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            Forgot password?
          </Link>
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={isLoading}
        >
          <ArrowRightEndOnRectangleIcon className="h-5 w-5" aria-hidden="true" />
          Sign In
        </Button>
      </motion.form>

      {/* Divider */}
      <div className="relative my-8">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-neutral-200" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-4 bg-white text-neutral-500">or</span>
        </div>
      </div>

      {/* Register Link */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="text-center mt-8 text-neutral-600"
      >
        Don't have an account?{' '}
        <Link
          to="/register"
          className="text-primary-600 hover:text-primary-700 font-semibold"
        >
          Create account
        </Link>
      </motion.p>
    </div>
  );
};

export default LoginPage;