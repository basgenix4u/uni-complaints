import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  PlusIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { Card, StatCard, Button, Spinner, EmptyState } from '../../components/ui';
import { StatusBadge, PriorityBadge } from '../../components/ui/StatusBadge';
import { studentService } from '../../services/api';
import { formatRelativeTime, getCategoryLabel } from '../../utils/helpers';
import useAuthStore from '../../stores/authStore';

const StudentDashboard = () => {
  const { user } = useAuthStore();

  // Fetch student stats
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['studentStats'],
    queryFn: () => studentService.getStats(),
  });

  const stats = statsData?.data?.statistics || {};
  const recentComplaints = statsData?.data?.recent_complaints || [];

  const statCards = [
    {
      title: 'Total Complaints',
      value: stats.total || 0,
      icon: DocumentTextIcon,
      color: 'primary',
    },
    {
      title: 'Pending',
      value: stats.pending || 0,
      icon: ClockIcon,
      color: 'warning',
    },
    {
      title: 'In Progress',
      value: stats.in_progress || 0,
      icon: ExclamationCircleIcon,
      color: 'info',
    },
    {
      title: 'Resolved',
      value: stats.resolved || 0,
      icon: CheckCircleIcon,
      color: 'success',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-primary-600 via-primary-700 to-primary-800 p-8 text-white"
      >
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0 bg-grid" />
        </div>
        
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, {user?.full_name?.split(' ')[0]}! 👋
          </h1>
          <p className="text-primary-100 mb-6 max-w-xl">
            Track your complaints and submit new requests. We're here to help you resolve any issues you face.
          </p>
          
          <Link to="/student/complaints/new">
            <Button
              variant="secondary"
              size="lg"
              leftIcon={<PlusIcon className="w-5 h-5" />}
              className="bg-white text-primary-700 hover:bg-primary-50 shadow-xl"
            >
              Submit New Complaint
            </Button>
          </Link>
        </div>

        {/* Decorative Elements */}
        <div className="absolute -right-10 -bottom-10 w-40 h-40 rounded-full bg-white/10" />
        <div className="absolute -right-5 -bottom-5 w-24 h-24 rounded-full bg-white/10" />
      </motion.div>

      {/* Stats Grid */}
      {statsLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 rounded-2xl bg-neutral-100 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat, index) => (
            <StatCard
              key={stat.title}
              title={stat.title}
              value={stat.value}
              icon={stat.icon}
              color={stat.color}
              delay={index * 0.1}
            />
          ))}
        </div>
      )}

      {/* Recent Complaints */}
      <Card animate delay={0.3}>
        <Card.Header>
          <div>
            <Card.Title>Recent Complaints</Card.Title>
            <Card.Description>Your latest submitted complaints</Card.Description>
          </div>
          <Link to="/student/complaints">
            <Button variant="ghost" size="sm" rightIcon={<ArrowRightIcon className="w-4 h-4" />}>
              View All
            </Button>
          </Link>
        </Card.Header>

        <Card.Content>
          {statsLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded-xl bg-neutral-100 animate-pulse" />
              ))}
            </div>
          ) : recentComplaints.length === 0 ? (
            <EmptyState
              icon={DocumentTextIcon}
              title="No complaints yet"
              description="You haven't submitted any complaints. Start by submitting your first complaint."
              actionLabel="Submit Complaint"
              onAction={() => window.location.href = '/student/complaints/new'}
            />
          ) : (
            <div className="space-y-4">
              {recentComplaints.map((complaint, index) => (
                <motion.div
                  key={complaint.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Link
                    to={`/student/complaints/${complaint.id}`}
                    className="block p-4 rounded-xl border border-neutral-100 hover:border-primary-200 hover:bg-primary-50/50 transition-all group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                            {complaint.ticket_number}
                          </span>
                          <StatusBadge status={complaint.status} />
                        </div>
                        <h4 className="font-medium text-neutral-900 group-hover:text-primary-700 transition-colors truncate">
                          {complaint.title}
                        </h4>
                        <div className="flex items-center gap-3 mt-2 text-sm text-neutral-500">
                          <span>{getCategoryLabel(complaint.category)}</span>
                          <span>•</span>
                          <span>{formatRelativeTime(complaint.created_at)}</span>
                        </div>
                      </div>
                      <PriorityBadge priority={complaint.priority} />
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </Card.Content>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card hover className="group cursor-pointer" onClick={() => window.location.href = '/student/complaints/new'}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-primary-100 flex items-center justify-center group-hover:bg-primary-200 transition-colors">
              <PlusIcon className="w-7 h-7 text-primary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-900">New Complaint</h3>
              <p className="text-sm text-neutral-500">Submit a new request</p>
            </div>
          </div>
        </Card>

        <Card hover className="group cursor-pointer" onClick={() => window.location.href = '/student/complaints'}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-secondary-100 flex items-center justify-center group-hover:bg-secondary-200 transition-colors">
              <DocumentTextIcon className="w-7 h-7 text-secondary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-900">Track Complaint</h3>
              <p className="text-sm text-neutral-500">Check status of requests</p>
            </div>
          </div>
        </Card>

        <Card hover className="group cursor-pointer" onClick={() => window.location.href = '/student/profile'}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-accent-100 flex items-center justify-center group-hover:bg-accent-200 transition-colors">
              <ExclamationCircleIcon className="w-7 h-7 text-accent-600" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-900">Need Help?</h3>
              <p className="text-sm text-neutral-500">Contact support team</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default StudentDashboard;