import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  UserIcon,
  EnvelopeIcon,
  PhoneIcon,
  BuildingOfficeIcon,
  AcademicCapIcon,
  LockClosedIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Input, Avatar, PageHeader } from '../../components/ui';
import useAuthStore from '../../stores/authStore';

// Validation Schemas
const profileSchema = z.object({
  full_name: z.string().min(3, 'Name must be at least 3 characters'),
  phone: z.string().optional(),
  department: z.string().optional(),
  faculty: z.string().optional(),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain uppercase letter')
    .regex(/[a-z]/, 'Must contain lowercase letter')
    .regex(/[0-9]/, 'Must contain number'),
  confirm_password: z.string().min(1, 'Please confirm password'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

const StudentProfile = () => {
  const { user, updateProfile, changePassword, isLoading } = useAuthStore();
  const [activeTab, setActiveTab] = useState('profile');

  // Profile Form
  const profileForm = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || '',
      phone: user?.phone || '',
      department: user?.department || '',
      faculty: user?.faculty || '',
    },
  });

  // Password Form
  const passwordForm = useForm({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const onProfileSubmit = async (data) => {
    const result = await updateProfile(data);
    if (result.success) {
      toast.success('Profile updated successfully');
    } else {
      toast.error(result.error || 'Failed to update profile');
    }
  };

  const onPasswordSubmit = async (data) => {
    const result = await changePassword({
      current_password: data.current_password,
      new_password: data.new_password,
    });
    if (result.success) {
      toast.success('Password changed successfully');
      passwordForm.reset();
    } else {
      toast.error(result.error || 'Failed to change password');
    }
  };

  const tabs = [
    { id: 'profile', label: 'Profile', icon: UserIcon },
    { id: 'security', label: 'Security', icon: LockClosedIcon },
  ];

  return (
    <div className="max-w-3xl mx-auto">
      <PageHeader
        title="My Profile"
        description="Manage your account settings and preferences"
      />

      {/* Profile Header Card */}
      <Card className="mb-6">
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <Avatar name={user?.full_name} size="2xl" />
          <div className="text-center sm:text-left">
            <h2 className="text-2xl font-bold text-neutral-900">{user?.full_name}</h2>
            <p className="text-neutral-500">{user?.email}</p>
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mt-2">
              <span className="badge-primary">Student</span>
              {user?.matric_number && (
                <span className="badge-secondary">{user?.matric_number}</span>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-neutral-200 pb-px overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 font-medium text-sm border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-700'
            }`}
          >
            <tab.icon className="w-5 h-5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'profile' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <h3 className="text-lg font-semibold text-neutral-900 mb-6">Personal Information</h3>
            
            <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <Input
                  label="Full Name"
                  leftIcon={<UserIcon className="w-5 h-5" />}
                  error={profileForm.formState.errors.full_name?.message}
                  {...profileForm.register('full_name')}
                />

                <Input
                  label="Email Address"
                  leftIcon={<EnvelopeIcon className="w-5 h-5" />}
                  value={user?.email}
                  disabled
                  hint="Email cannot be changed"
                />

                <Input
                  label="Matric Number"
                  leftIcon={<AcademicCapIcon className="w-5 h-5" />}
                  value={user?.matric_number}
                  disabled
                  hint="Matric number cannot be changed"
                />

                <Input
                  label="Phone Number"
                  leftIcon={<PhoneIcon className="w-5 h-5" />}
                  placeholder="e.g., 08012345678"
                  error={profileForm.formState.errors.phone?.message}
                  {...profileForm.register('phone')}
                />

                <Input
                  label="Department"
                  leftIcon={<BuildingOfficeIcon className="w-5 h-5" />}
                  error={profileForm.formState.errors.department?.message}
                  {...profileForm.register('department')}
                />

                <Input
                  label="Faculty"
                  leftIcon={<AcademicCapIcon className="w-5 h-5" />}
                  error={profileForm.formState.errors.faculty?.message}
                  {...profileForm.register('faculty')}
                />
              </div>

              <div className="flex justify-end pt-4 border-t border-neutral-100">
                <Button
                  type="submit"
                  loading={isLoading}
                  leftIcon={<CheckIcon className="w-5 h-5" />}
                >
                  Save Changes
                </Button>
              </div>
            </form>
          </Card>
        </motion.div>
      )}

      {activeTab === 'security' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <h3 className="text-lg font-semibold text-neutral-900 mb-6">Change Password</h3>
            
            <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-6">
              <Input
                label="Current Password"
                type="password"
                leftIcon={<LockClosedIcon className="w-5 h-5" />}
                error={passwordForm.formState.errors.current_password?.message}
                {...passwordForm.register('current_password')}
              />

              <Input
                label="New Password"
                type="password"
                leftIcon={<LockClosedIcon className="w-5 h-5" />}
                hint="Min 8 chars, 1 uppercase, 1 lowercase, 1 number"
                error={passwordForm.formState.errors.new_password?.message}
                {...passwordForm.register('new_password')}
              />

              <Input
                label="Confirm New Password"
                type="password"
                leftIcon={<LockClosedIcon className="w-5 h-5" />}
                error={passwordForm.formState.errors.confirm_password?.message}
                {...passwordForm.register('confirm_password')}
              />

              <div className="flex justify-end pt-4 border-t border-neutral-100">
                <Button
                  type="submit"
                  loading={isLoading}
                  leftIcon={<CheckIcon className="w-5 h-5" />}
                >
                  Change Password
                </Button>
              </div>
            </form>
          </Card>
        </motion.div>
      )}
    </div>
  );
};

export default StudentProfile;