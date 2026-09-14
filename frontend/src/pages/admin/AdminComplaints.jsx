import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FunnelIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DocumentTextIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Select, Spinner, EmptyState, PageHeader, Avatar } from '../../components/ui';
import { StatusBadge, PriorityBadge } from '../../components/ui/StatusBadge';
import { adminService } from '../../services/api';
import { formatRelativeTime, getCategoryLabel, getCategoryIcon } from '../../utils/helpers';
import { CATEGORIES } from '../../utils/constants';

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
  { value: 'rejected', label: 'Rejected' },
];

const priorityOptions = [
  { value: '', label: 'All Priorities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
];

const categoryOptions = [
  { value: '', label: 'All Categories' },
  ...CATEGORIES.map(c => ({ value: c.value, label: c.label })),
];

const AdminComplaints = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showFilters, setShowFilters] = useState(false);
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');

  const page = parseInt(searchParams.get('page') || '1');
  const status = searchParams.get('status') || '';
  const priority = searchParams.get('priority') || '';
  const category = searchParams.get('category') || '';
  const search = searchParams.get('search') || '';
  const unassigned = searchParams.get('unassigned') === 'true';

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['adminComplaints', { page, status, priority, category, search, unassigned }],
    queryFn: () => adminService.getAllComplaints({ page, per_page: 10, status, priority, category, search, unassigned }),
    keepPreviousData: true,
  });

  const complaints = data?.data?.complaints || [];
  const pagination = data?.data?.pagination || {};

  const updateParams = (newParams) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(newParams).forEach(([key, value]) => {
      if (value) {
        params.set(key, String(value));
      } else {
        params.delete(key);
      }
    });
    if (!newParams.page) {
      params.set('page', '1');
    }
    setSearchParams(params);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    updateParams({ search: searchInput });
  };

  const clearFilters = () => {
    setSearchInput('');
    setSearchParams({});
  };

  const hasActiveFilters = status || priority || category || search || unassigned;

  return (
    <div className="space-y-6">
      <PageHeader
        title="All Complaints"
        description="Manage and respond to all student complaints"
      />

      {/* Quick Filters */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={!hasActiveFilters ? 'primary' : 'outline'}
          size="sm"
          onClick={clearFilters}
        >
          All
        </Button>
        <Button
          variant={status === 'pending' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => updateParams({ status: 'pending' })}
        >
          Pending
        </Button>
        <Button
          variant={status === 'in_progress' ? 'primary' : 'outline'}
          size="sm"
          onClick={() => updateParams({ status: 'in_progress' })}
        >
          In Progress
        </Button>
        <Button
          variant={unassigned ? 'primary' : 'outline'}
          size="sm"
          onClick={() => updateParams({ unassigned: !unassigned ? 'true' : '' })}
        >
          Unassigned
        </Button>
        <Button
          variant={priority === 'urgent' ? 'danger' : 'outline'}
          size="sm"
          onClick={() => updateParams({ priority: 'urgent' })}
        >
          🔴 Urgent
        </Button>
      </div>

      <Card padding={false}>
        {/* Search & Filters */}
        <div className="p-4 border-b border-neutral-100">
          <div className="flex flex-col sm:flex-row gap-4">
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search tickets, titles, student names..."
                  className="w-full pl-11 pr-4 py-2.5 bg-neutral-50 border-0 rounded-xl text-sm placeholder:text-neutral-400 focus:bg-white focus:ring-2 focus:ring-primary-500/20 transition-all"
                />
              </div>
            </form>
            <Button
              variant={showFilters ? 'primary' : 'outline'}
              leftIcon={<FunnelIcon className="w-5 h-5" />}
              onClick={() => setShowFilters(!showFilters)}
            >
              Filters
            </Button>
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Select
                    label="Status"
                    options={statusOptions}
                    value={status}
                    onChange={(value) => updateParams({ status: value })}
                  />
                  <Select
                    label="Priority"
                    options={priorityOptions}
                    value={priority}
                    onChange={(value) => updateParams({ priority: value })}
                  />
                  <Select
                    label="Category"
                    options={categoryOptions}
                    value={category}
                    onChange={(value) => updateParams({ category: value })}
                  />
                  <div className="flex items-end">
                    <Button variant="ghost" onClick={clearFilters} disabled={!hasActiveFilters}>
                      Clear All
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Results */}
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100 flex items-center justify-between">
          <p className="text-sm text-neutral-600">
            {pagination.total_items || 0} complaint{pagination.total_items !== 1 ? 's' : ''}
          </p>
          {isFetching && <Spinner size="sm" />}
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 rounded-xl bg-neutral-100 animate-pulse" />
              ))}
            </div>
          ) : complaints.length === 0 ? (
            <EmptyState
              icon={DocumentTextIcon}
              title="No complaints found"
              description={hasActiveFilters ? 'Try adjusting your filters' : 'No complaints have been submitted yet'}
              actionLabel={hasActiveFilters ? 'Clear Filters' : undefined}
              onAction={hasActiveFilters ? clearFilters : undefined}
            />
          ) : (
            <table className="w-full">
              <thead className="bg-neutral-50 border-b border-neutral-100">
                <tr>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase">Ticket</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase">Student</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase hidden lg:table-cell">Category</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase">Status</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase hidden md:table-cell">Priority</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-500 uppercase hidden xl:table-cell">Assigned</th>
                  <th className="text-right px-6 py-4 text-xs font-semibold text-neutral-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {complaints.map((complaint, index) => (
                  <motion.tr
                    key={complaint.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.03 }}
                    className="hover:bg-neutral-50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-xs font-mono text-primary-600 bg-primary-50 px-2 py-0.5 rounded inline-block">
                          {complaint.ticket_number}
                        </p>
                        <p className="font-medium text-neutral-900 mt-1 line-clamp-1 max-w-[200px]">
                          {complaint.title}
                        </p>
                        <p className="text-xs text-neutral-400 mt-0.5">
                          {formatRelativeTime(complaint.created_at)}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <Avatar name={complaint.student?.full_name} size="sm" />
                        <div>
                          <p className="font-medium text-neutral-900 text-sm">
                            {complaint.student?.full_name}
                          </p>
                          <p className="text-xs text-neutral-500">
                            {complaint.student?.matric_number}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 hidden lg:table-cell">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{getCategoryIcon(complaint.category)}</span>
                        <span className="text-sm text-neutral-600">{getCategoryLabel(complaint.category)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={complaint.status} />
                    </td>
                    <td className="px-6 py-4 hidden md:table-cell">
                      <PriorityBadge priority={complaint.priority} />
                    </td>
                    <td className="px-6 py-4 hidden xl:table-cell">
                      {complaint.assigned_admin ? (
                        <div className="flex items-center gap-2">
                          <Avatar name={complaint.assigned_admin.full_name} size="sm" />
                          <span className="text-sm text-neutral-600">
                            {complaint.assigned_admin.full_name}
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-neutral-400">Unassigned</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link to={`/admin/complaints/${complaint.id}`}>
                        <Button variant="ghost" size="sm" leftIcon={<EyeIcon className="w-4 h-4" />}>
                          View
                        </Button>
                      </Link>
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
    </div>
  );
};

export default AdminComplaints;