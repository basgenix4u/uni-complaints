import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  UserIcon,
  LockClosedIcon,
  BellIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Input, Avatar, PageHeader } from '../../components/ui';
import useAuthStore from '../../stores/authStore';

// Validation Schemas
const profileSchema = z.object({
  full_name: z.string().min(3, 'Name must be at least 3 characters'),
  phone: z.string().optional(),
  department: z.string().optional(),
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

const AdminSettings = () => {
  const { user, updateProfile, changePassword, isLoading } = useAuthStore();
  const [activeTab, setActiveTab] = useState('profile');

  const profileForm = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || '',
      phone: user?.phone || '',
      department: user?.department || '',
    },
  });

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
    { id: 'notifications', label: 'Notifications', icon: BellIcon },
  ];

  const getRoleLabel = (role) => {
    const labels = {
      admin: 'Administrator',
      super_admin: 'Super Administrator',
    };
    return labels[role] || role;
  };

  return (
    <div className="max-w-3xl mx-auto">
      <PageHeader
        title="Settings"
        description="Manage your account and preferences"
      />

      {/* Profile Header */}
      <Card className="mb-6">
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <Avatar name={user?.full_name} size="2xl" />
          <div className="text-center sm:text-left">
            <h2 className="text-2xl font-bold text-neutral-900">{user?.full_name}</h2>
            <p className="text-neutral-500">{user?.email}</p>
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mt-2">
              <span className="badge-primary">{getRoleLabel(user?.role)}</span>
              {user?.department && (
                <span className="badge-secondary">{user?.department}</span>
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
            <h3 className="text-lg font-semibold text-neutral-900 mb-6">Profile Information</h3>
            
            <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-6">
              <Input
                label="Full Name"
                leftIcon={<UserIcon className="w-5 h-5" />}
                error={profileForm.formState.errors.full_name?.message}
                {...profileForm.register('full_name')}
              />

              <Input
                label="Email Address"
                value={user?.email}
                disabled
                hint="Email cannot be changed"
              />

              <Input
                label="Phone Number"
                placeholder="e.g., 08012345678"
                error={profileForm.formState.errors.phone?.message}
                {...profileForm.register('phone')}
              />

              <Input
                label="Department"
                placeholder="e.g., Student Affairs"
                error={profileForm.formState.errors.department?.message}
                {...profileForm.register('department')}
              />

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

      {activeTab === 'notifications' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <h3 className="text-lg font-semibold text-neutral-900 mb-6">Notification Preferences</h3>
            
            <div className="space-y-6">
              {[
                { id: 'new_complaints', label: 'New Complaints', description: 'Get notified when new complaints are submitted' },
                { id: 'assigned', label: 'Assignment Notifications', description: 'Get notified when complaints are assigned to you' },
                { id: 'responses', label: 'Response Notifications', description: 'Get notified when students respond to complaints' },
                { id: 'reports', label: 'Weekly Reports', description: 'Receive weekly summary reports via email' },
              ].map((item) => (
                <div key={item.id} className="flex items-center justify-between py-3 border-b border-neutral-100 last:border-0">
                  <div>
                    <p className="font-medium text-neutral-900">{item.label}</p>
                    <p className="text-sm text-neutral-500">{item.description}</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="sr-only peer" />
                    <div className="w-11 h-6 bg-neutral-200 peer-focus:ring-4 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-6 border-t border-neutral-100 mt-6">
              <Button leftIcon={<CheckIcon className="w-5 h-5" />}>
                Save Preferences
              </Button>
            </div>
          </Card>
        </motion.div>
      )}
    </div>
  );
};

export default AdminSettings;