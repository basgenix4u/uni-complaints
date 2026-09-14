import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Input, Select, Spinner, EmptyState, PageHeader } from '../../components/ui';
import { StatusBadge, PriorityBadge } from '../../components/ui/StatusBadge';
import { studentService } from '../../services/api';
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

const categoryOptions = [
  { value: '', label: 'All Categories' },
  ...CATEGORIES.map(c => ({ value: c.value, label: c.label })),
];

const MyComplaints = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showFilters, setShowFilters] = useState(false);

  // Get filter values from URL
  const page = parseInt(searchParams.get('page') || '1');
  const status = searchParams.get('status') || '';
  const category = searchParams.get('category') || '';
  const search = searchParams.get('search') || '';

  // Local state for search input
  const [searchInput, setSearchInput] = useState(search);

  // Fetch complaints
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['myComplaints', { page, status, category, search }],
    queryFn: () => studentService.getMyComplaints({ page, per_page: 10, status, category, search }),
    keepPreviousData: true,
  });

  const complaints = data?.data?.complaints || [];
  const pagination = data?.data?.pagination || {};

  // Update URL params
  const updateParams = (newParams) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(newParams).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    });
    // Reset to page 1 when filters change
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

  const hasActiveFilters = status || category || search;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="My Complaints"
        description="View and track all your submitted complaints"
        action={
          <Link to="/student/complaints/new">
            <Button leftIcon={<PlusIcon className="w-5 h-5" />}>
              New Complaint
            </Button>
          </Link>
        }
      />

      {/* Filters Section */}
      <Card padding={false}>
        <div className="p-4 border-b border-neutral-100">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search by ticket number or title..."
                  className="w-full pl-11 pr-4 py-2.5 bg-neutral-50 border-0 rounded-xl text-sm placeholder:text-neutral-400 focus:bg-white focus:ring-2 focus:ring-primary-500/20 transition-all"
                />
              </div>
            </form>

            {/* Filter Toggle */}
            <Button
              variant={showFilters ? 'primary' : 'outline'}
              leftIcon={<FunnelIcon className="w-5 h-5" />}
              onClick={() => setShowFilters(!showFilters)}
            >
              Filters
              {hasActiveFilters && (
                <span className="ml-1 w-2 h-2 rounded-full bg-primary-500" />
              )}
            </Button>
          </div>

          {/* Expandable Filters */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Select
                    label="Status"
                    options={statusOptions}
                    value={status}
                    onChange={(value) => updateParams({ status: value })}
                    placeholder="All Statuses"
                  />
                  <Select
                    label="Category"
                    options={categoryOptions}
                    value={category}
                    onChange={(value) => updateParams({ category: value })}
                    placeholder="All Categories"
                  />
                  <div className="sm:col-span-2 flex items-end">
                    <Button
                      variant="ghost"
                      onClick={clearFilters}
                      disabled={!hasActiveFilters}
                      className="w-full sm:w-auto"
                    >
                      Clear Filters
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Results Count */}
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100 flex items-center justify-between">
          <p className="text-sm text-neutral-600">
            {pagination.total_items || 0} complaint{pagination.total_items !== 1 ? 's' : ''} found
          </p>
          {isFetching && <Spinner size="sm" />}
        </div>

        {/* Complaints List */}
        <div className="divide-y divide-neutral-100">
          {isLoading ? (
            <div className="p-8">
              <div className="space-y-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-24 rounded-xl bg-neutral-100 animate-pulse" />
                ))}
              </div>
            </div>
          ) : complaints.length === 0 ? (
            <EmptyState
              icon={DocumentTextIcon}
              title={hasActiveFilters ? 'No complaints match your filters' : 'No complaints yet'}
              description={
                hasActiveFilters
                  ? 'Try adjusting your filters or search terms'
                  : "You haven't submitted any complaints. Start by submitting your first complaint."
              }
              actionLabel={hasActiveFilters ? 'Clear Filters' : 'Submit Complaint'}
              onAction={hasActiveFilters ? clearFilters : () => window.location.href = '/student/complaints/new'}
            />
          ) : (
            complaints.map((complaint, index) => (
              <motion.div
                key={complaint.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Link
                  to={`/student/complaints/${complaint.id}`}
                  className="block p-4 sm:p-6 hover:bg-neutral-50 transition-colors group"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                    {/* Category Icon */}
                    <div className="hidden sm:flex w-12 h-12 rounded-xl bg-primary-50 items-center justify-center text-2xl flex-shrink-0">
                      {getCategoryIcon(complaint.category)}
                    </div>

                    {/* Main Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                          {complaint.ticket_number}
                        </span>
                        <StatusBadge status={complaint.status} />
                        <PriorityBadge priority={complaint.priority} />
                      </div>
                      
                      <h3 className="font-semibold text-neutral-900 group-hover:text-primary-600 transition-colors line-clamp-1">
                        {complaint.title}
                      </h3>
                      
                      <p className="text-sm text-neutral-500 line-clamp-1 mt-1">
                        {complaint.description}
                      </p>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-neutral-400">
                        <span>{getCategoryLabel(complaint.category)}</span>
                        <span>•</span>
                        <span>{formatRelativeTime(complaint.created_at)}</span>
                        {complaint.response_count > 0 && (
                          <>
                            <span>•</span>
                            <span>{complaint.response_count} response{complaint.response_count !== 1 ? 's' : ''}</span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Arrow */}
                    <ChevronRightIcon className="w-5 h-5 text-neutral-300 group-hover:text-primary-500 transition-colors hidden sm:block" />
                  </div>
                </Link>
              </motion.div>
            ))
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

export default MyComplaints;