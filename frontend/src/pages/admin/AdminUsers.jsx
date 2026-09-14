import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  UserPlusIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  UsersIcon,
  ShieldCheckIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Input, Select, Spinner, EmptyState, Modal, Avatar, PageHeader } from '../../components/ui';
import { adminService, authService } from '../../services/api';
import { formatDate } from '../../utils/helpers';
import useAuthStore from '../../stores/authStore';

const roleOptions = [
  { value: '', label: 'All Roles' },
  { value: 'student', label: 'Student' },
  { value: 'admin', label: 'Admin' },
  { value: 'super_admin', label: 'Super Admin' },
];

const newAdminSchema = z.object({
  full_name: z.string().min(3, 'Name must be at least 3 characters'),
  email: z.string().email('Please enter a valid email'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain uppercase letter')
    .regex(/[a-z]/, 'Must contain lowercase letter')
    .regex(/[0-9]/, 'Must contain number'),
  role: z.enum(['admin', 'super_admin']),
  department: z.string().optional(),
  phone: z.string().optional(),
});

const AdminUsers = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const queryClient = useQueryClient();
  const { isSuperAdmin } = useAuthStore();

  const page = parseInt(searchParams.get('page') || '1');
  const role = searchParams.get('role') || '';
  const search = searchParams.get('search') || '';

  // --- FIX START: Hooks moved to the top ---
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['adminUsers', { page, role, search }],
    queryFn: () => adminService.getAllUsers({ page, per_page: 10, role, search }),
    keepPreviousData: true,
    enabled: isSuperAdmin(), // Only run query if user is super admin
  });

  const users = data?.data?.users || [];
  const pagination = data?.data?.pagination || {};

  const toggleActiveMutation = useMutation({
    mutationFn: (userId) => adminService.toggleUserActive(userId),
    onSuccess: (response) => {
      const status = response.data?.user?.is_active ? 'activated' : 'deactivated';
      toast.success(`User ${status} successfully`);
      queryClient.invalidateQueries(['adminUsers']);
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to update user');
    },
  });

  const createAdminMutation = useMutation({
    mutationFn: (data) => authService.registerAdmin(data),
    onSuccess: () => {
      toast.success('Admin account created successfully');
      setShowAddModal(false);
      queryClient.invalidateQueries(['adminUsers']);
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to create admin');
    },
  });
  // --- FIX END: Hooks are now safe ---

  const updateParams = (newParams) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(newParams).forEach(([key, value]) => {
      if (value) {
        params.set(key, String(value));
      } else {
        params.delete(key);
      }
    });
    if (!newParams.page) params.set('page', '1');
    setSearchParams(params);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    updateParams({ search: searchInput });
  };

  const getRoleBadge = (role) => {
    const badges = {
      student: 'badge-secondary',
      admin: 'badge-primary',
      super_admin: 'badge-success',
    };
    const labels = {
      student: 'Student',
      admin: 'Admin',
      super_admin: 'Super Admin',
    };
    return <span className={badges[role] || 'badge-secondary'}>{labels[role] || role}</span>;
  };

  // --- ACCESS CHECK IS NOW HERE (After hooks) ---
  if (!isSuperAdmin()) {
    return (
      <div className="text-center py-16">
        <ShieldCheckIcon className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-neutral-900 mb-2">Access Denied</h2>
        <p className="text-neutral-500">Only super admins can access user management.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        description="Manage students and administrators"
        action={
          <Button
            leftIcon={<UserPlusIcon className="w-5 h-5" />}
            onClick={() => setShowAddModal(true)}
          >
            Add Admin
          </Button>
        }
      />

      <Card padding={false}>
        {/* Filters */}
        <div className="p-4 border-b border-neutral-100">
          <div className="flex flex-col sm:flex-row gap-4">
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search by name, email, or matric number..."
                  className="w-full pl-11 pr-4 py-2.5 bg-neutral-50 border-0 rounded-xl text-sm placeholder:text-neutral-400 focus:bg-white focus:ring-2 focus:ring-primary-500/20 transition-all"
                />
              </div>
            </form>
            <Select
              options={roleOptions}
              value={role}
              onChange={(value) => updateParams({ role: value })}
              placeholder="Filter by role"
              className="w-40"
            />
          </div>
        </div>

        {/* Results */}
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100 flex items-center justify-between">
          <p className="text-sm text-neutral-600">
            {pagination.total_items || 0} user{pagination.total_items !== 1 ? 's' : ''}
          </p>
          {isFetching && <Spinner size="sm" />}
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 rounded-xl bg-neutral-100 animate-pulse" />
              ))}
            </div>
          ) : users.length === 0 ? (
            <EmptyState
              icon={UsersIcon}
              title="No users found"
              description="No users match your search criteria"
            />
          ) : (
            <table className="w-full">
              <thead className="bg-neutral-50 border-b border-neutral-100">
                <tr>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase">User</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase hidden md:table-cell">Role</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase hidden lg:table-cell">Department</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase hidden xl:table-cell">Joined</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase">Status</th>
                  <th className="text-right px-6 py-4 text-xs font-semibold text-neutral-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {users.map((user, index) => (
                  <motion.tr
                    key={user.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.03 }}
                    className="hover:bg-neutral-50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <Avatar name={user.full_name} size="md" />
                        <div>
                          <p className="font-medium text-neutral-900">{user.full_name}</p>
                          <p className="text-sm text-neutral-500">{user.email}</p>
                          {user.matric_number && (
                            <p className="text-xs text-neutral-400">{user.matric_number}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 hidden md:table-cell">
                      {getRoleBadge(user.role)}
                    </td>
                    <td className="px-6 py-4 hidden lg:table-cell">
                      <p className="text-sm text-neutral-600">{user.department || '-'}</p>
                    </td>
                    <td className="px-6 py-4 hidden xl:table-cell">
                      <p className="text-sm text-neutral-600">{formatDate(user.created_at, 'MMM dd, yyyy')}</p>
                    </td>
                    <td className="px-6 py-4">
                      {user.is_active ? (
                        <span className="inline-flex items-center gap-1 text-sm text-success-600">
                          <CheckCircleIcon className="w-4 h-4" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-sm text-neutral-400">
                          <XCircleIcon className="w-4 h-4" />
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        variant={user.is_active ? 'outline' : 'success'}
                        size="sm"
                        onClick={() => toggleActiveMutation.mutate(user.id)}
                        loading={toggleActiveMutation.isPending}
                      >
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {pagination.total_pages > 1 && (
          <div className="p-4 border-t border-neutral-100 flex items-center justify-between">
            <p className="text-sm text-neutral-500">
              Page {pagination.page} of {pagination.total_pages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!pagination.has_prev}
                onClick={() => updateParams({ page: page - 1 })}
                leftIcon={<ChevronLeftIcon className="w-4 h-4" />}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!pagination.has_next}
                onClick={() => updateParams({ page: page + 1 })}
                rightIcon={<ChevronRightIcon className="w-4 h-4" />}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Add Admin Modal */}
      <AddAdminModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={(data) => createAdminMutation.mutate(data)}
        isLoading={createAdminMutation.isPending}
      />
    </div>
  );
};

// Add Admin Modal Component
const AddAdminModal = ({ isOpen, onClose, onSubmit, isLoading }) => {
  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm({
    resolver: zodResolver(newAdminSchema),
    defaultValues: {
      full_name: '',
      email: '',
      password: '',
      role: 'admin',
      department: '',
      phone: '',
    },
  });

  const watchRole = watch('role');

  const handleClose = () => {
    reset();
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Admin Account" size="lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Full Name"
            placeholder="Enter full name"
            error={errors.full_name?.message}
            {...register('full_name')}
          />
          <Input
            label="Email Address"
            type="email"
            placeholder="admin@university.edu.ng"
            error={errors.email?.message}
            {...register('email')}
          />
          <Input
            label="Password"
            type="password"
            placeholder="Create a strong password"
            error={errors.password?.message}
            {...register('password')}
          />
          <Select
            label="Role"
            options={[
              { value: 'admin', label: 'Admin' },
              { value: 'super_admin', label: 'Super Admin' },
            ]}
            value={watchRole}
            onChange={(value) => setValue('role', value)}
            error={errors.role?.message}
          />
          <Input
            label="Department (Optional)"
            placeholder="e.g., Student Affairs"
            error={errors.department?.message}
            {...register('department')}
          />
          <Input
            label="Phone (Optional)"
            placeholder="e.g., 08012345678"
            error={errors.phone?.message}
            {...register('phone')}
          />
        </div>

        <Modal.Footer>
          <Button variant="outline" onClick={handleClose} type="button">Cancel</Button>
          <Button type="submit" loading={isLoading}>Create Admin</Button>
        </Modal.Footer>
      </form>
    </Modal>
  );
};

export default AdminUsers;