import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  EnvelopeIcon,
  LockClosedIcon,
  UserIcon,
  IdentificationIcon,
  BuildingOfficeIcon,
  PhoneIcon,
} from '@heroicons/react/24/outline';
import { Button, Input, Select } from '../../components/ui';
import useAuthStore from '../../stores/authStore';

// Validation Schema
const registerSchema = z.object({
  full_name: z
    .string()
    .min(1, 'Full name is required')
    .min(3, 'Name must be at least 3 characters'),
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email'),
  // UPDATED: New Regex to support ENG/COE/21/013 format
  matric_number: z
    .string()
    .min(1, 'Matric number is required')
    .regex(
      /^[A-Za-z]{2,5}\/[A-Za-z]{2,5}\/\d{2,4}\/\d{3,6}$/, 
      'Format example: ENG/COE/21/013'
    ),
  department: z
    .string()
    .min(1, 'Department is required'),
  faculty: z
    .string()
    .min(1, 'Faculty is required'),
  phone: z
    .string()
    .optional(),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirm_password: z
    .string()
    .min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

const faculties = [
  { value: 'science', label: 'Science' },
  { value: 'engineering', label: 'Engineering' },
  { value: 'arts', label: 'Arts' },
  { value: 'social_sciences', label: 'Social Sciences' },
  { value: 'management_sciences', label: 'Management Sciences' },
  { value: 'law', label: 'Law' },
  { value: 'medicine', label: 'Medicine & Health Sciences' },
  { value: 'education', label: 'Education' },
  { value: 'agriculture', label: 'Agriculture' },
  { value: 'environmental_sciences', label: 'Environmental Sciences' },
];

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register: registerUser, isLoading } = useAuthStore();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(registerSchema),
    mode: 'onSubmit', // <--- FIXED: Prevents crash while typing
    defaultValues: {
      full_name: '',
      email: '',
      matric_number: '',
      department: '',
      faculty: '',
      phone: '',
      password: '',
      confirm_password: '',
    },
  });

  // eslint-disable-next-line react-hooks/incompatible-library
  const watchFaculty = watch('faculty');

  const onSubmit = async (data) => {
    try {
      // Remove confirm_password before sending
      const { confirm_password, ...registerData } = data;
      
      const result = await registerUser(registerData);
      
      if (result.success) {
        toast.success('Account created successfully!');
        navigate('/student/dashboard');
      } else {
        toast.error(result.error || 'Registration failed');
      }
    } catch (error) {
      console.error("Registration Error:", error);
      toast.error("An unexpected error occurred.");
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl font-bold text-neutral-900 mb-2"
        >
          Create Account
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-neutral-500"
        >
          Register to start submitting complaints
        </motion.p>
      </div>

      {/* Form */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
      >
        {/* Full Name */}
        <Input
          label="Full Name"
          placeholder="Enter your full name"
          leftIcon={<UserIcon className="w-5 h-5" />}
          error={errors.full_name?.message}
          {...register('full_name')}
        />

        {/* Email */}
        <Input
          label="Email Address"
          type="email"
          placeholder="your.email@university.edu.ng"
          leftIcon={<EnvelopeIcon className="w-5 h-5" />}
          error={errors.email?.message}
          {...register('email')}
        />

        {/* Matric Number - UPDATED */}
        <Input
          label="Matric Number"
          // Placeholder removed as requested
          leftIcon={<IdentificationIcon className="w-5 h-5" />}
          error={errors.matric_number?.message}
          hint="Format: ENG/COE/21/013"
          {...register('matric_number')}
        />

        {/* Faculty & Department */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Select
            label="Faculty"
            placeholder="Select faculty"
            options={faculties}
            value={watchFaculty}
            onChange={(value) => setValue('faculty', value)}
            error={errors.faculty?.message}
          />

          <Input
            label="Department"
            placeholder="e.g., Computer Science"
            leftIcon={<BuildingOfficeIcon className="w-5 h-5" />}
            error={errors.department?.message}
            {...register('department')}
          />
        </div>

        {/* Phone */}
        <Input
          label="Phone Number (Optional)"
          type="tel"
          placeholder="e.g., 08012345678"
          leftIcon={<PhoneIcon className="w-5 h-5" />}
          error={errors.phone?.message}
          {...register('phone')}
        />

        {/* Password */}
        <Input
          label="Password"
          type="password"
          placeholder="Create a strong password"
          leftIcon={<LockClosedIcon className="w-5 h-5" />}
          error={errors.password?.message}
          hint="Min 8 chars, 1 uppercase, 1 lowercase, 1 number"
          {...register('password')}
        />

        {/* Confirm Password */}
        <Input
          label="Confirm Password"
          type="password"
          placeholder="Confirm your password"
          leftIcon={<LockClosedIcon className="w-5 h-5" />}
          error={errors.confirm_password?.message}
          {...register('confirm_password')}
        />

        {/* Terms */}
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            required
            className="w-4 h-4 mt-0.5 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-neutral-600">
            I agree to the{' '}
            <Link to="/terms" className="text-primary-600 hover:underline">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link to="/privacy" className="text-primary-600 hover:underline">
              Privacy Policy
            </Link>
          </span>
        </label>

        {/* Submit Button */}
        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={isLoading}
          className="mt-6"
        >
          Create Account
        </Button>
      </motion.form>

      {/* Login Link */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="text-center mt-6 text-neutral-600"
      >
        Already have an account?{' '}
        <Link
          to="/login"
          className="text-primary-600 hover:text-primary-700 font-semibold"
        >
          Sign in
        </Link>
      </motion.p>
    </div>
  );
};

export default RegisterPage;