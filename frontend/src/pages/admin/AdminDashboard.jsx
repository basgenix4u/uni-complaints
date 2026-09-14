import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  UsersIcon,
  ArrowTrendingUpIcon,
  ExclamationCircleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import { Card, StatCard, Button, Spinner } from '../../components/ui';
import { StatusBadge, PriorityBadge } from '../../components/ui/StatusBadge';
import { dashboardService } from '../../services/api';
import { formatRelativeTime, getCategoryLabel } from '../../utils/helpers';
import useAuthStore from '../../stores/authStore';

const COLORS = ['#f59e0b', '#3b82f6', '#22c55e', '#6b7280', '#ef4444'];

const AdminDashboard = () => {
  const { user } = useAuthStore();

  // Fetch dashboard data
  const { data: overviewData, isLoading: overviewLoading } = useQuery({
    queryKey: ['dashboardOverview'],
    queryFn: () => dashboardService.getOverview(),
  });

  const { data: statusChartData } = useQuery({
    queryKey: ['statusChart'],
    queryFn: () => dashboardService.getStatusChart(),
  });

  const { data: categoryChartData } = useQuery({
    queryKey: ['categoryChart'],
    queryFn: () => dashboardService.getCategoryChart(),
  });

  const { data: trendChartData } = useQuery({
    queryKey: ['trendChart'],
    queryFn: () => dashboardService.getTrendChart(14),
  });

  const overview = overviewData?.data?.overview || {};
  const statusCounts = overviewData?.data?.status_counts || {};
  const todayStats = overviewData?.data?.today || {};
  const recentComplaints = overviewData?.data?.recent_complaints || [];

  const statusChart = statusChartData?.data?.chart_data || [];
  const categoryChart = categoryChartData?.data?.chart_data?.slice(0, 6) || [];
  const trendChart = trendChartData?.data?.chart_data || [];

  const statCards = [
    {
      title: 'Total Complaints',
      value: overview.total_complaints || 0,
      icon: DocumentTextIcon,
      color: 'primary',
    },
    {
      title: 'Pending',
      value: statusCounts.pending || 0,
      icon: ClockIcon,
      color: 'warning',
    },
    {
      title: 'In Progress',
      value: statusCounts.in_progress || 0,
      icon: ExclamationCircleIcon,
      color: 'info',
    },
    {
      title: 'Resolved',
      value: statusCounts.resolved || 0,
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
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">
            Welcome back, {user?.full_name?.split(' ')[0]}! 👋
          </h1>
          <p className="text-neutral-500 mt-1">
            Here's what's happening with complaints today.
          </p>
        </div>
        <div className="flex gap-3">
          <Card padding={false} className="px-4 py-3">
            <div className="text-center">
              <p className="text-2xl font-bold text-primary-600">{todayStats.new || 0}</p>
              <p className="text-xs text-neutral-500">New Today</p>
            </div>
          </Card>
          <Card padding={false} className="px-4 py-3">
            <div className="text-center">
              <p className="text-2xl font-bold text-success-600">{todayStats.resolved || 0}</p>
              <p className="text-xs text-neutral-500">Resolved Today</p>
            </div>
          </Card>
        </div>
      </motion.div>

      {/* Stats Grid */}
      {overviewLoading ? (
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

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <Card>
          <Card.Header>
            <Card.Title>Status Distribution</Card.Title>
          </Card.Header>
          <Card.Content>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusChart}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="count"
                    nameKey="label"
                  >
                    {statusChart.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e5e5',
                      borderRadius: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              {statusChart.map((item, index) => (
                <div key={item.status} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-sm text-neutral-600">{item.label}: {item.count}</span>
                </div>
              ))}
            </div>
          </Card.Content>
        </Card>

        {/* Category Distribution */}
        <Card>
          <Card.Header>
            <Card.Title>Top Categories</Card.Title>
          </Card.Header>
          <Card.Content>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryChart} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={100}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e5e5',
                      borderRadius: '12px',
                    }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card.Content>
        </Card>
      </div>

      {/* Trend Chart */}
      <Card>
        <Card.Header>
          <Card.Title>Complaints Trend (Last 14 Days)</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                  }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e5e5',
                    borderRadius: '12px',
                  }}
                  labelFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card.Content>
      </Card>

      {/* Recent Complaints */}
      <Card>
        <Card.Header>
          <div>
            <Card.Title>Recent Complaints</Card.Title>
            <Card.Description>Latest complaints requiring attention</Card.Description>
          </div>
          <Link to="/admin/complaints">
            <Button variant="ghost" size="sm" rightIcon={<ArrowRightIcon className="w-4 h-4" />}>
              View All
            </Button>
          </Link>
        </Card.Header>
        <Card.Content>
          {overviewLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded-xl bg-neutral-100 animate-pulse" />
              ))}
            </div>
          ) : recentComplaints.length === 0 ? (
            <p className="text-center text-neutral-500 py-8">No complaints yet</p>
          ) : (
            <div className="space-y-4">
              {recentComplaints.slice(0, 5).map((complaint, index) => (
                <motion.div
                  key={complaint.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Link
                    to={`/admin/complaints/${complaint.id}`}
                    className="block p-4 rounded-xl border border-neutral-100 hover:border-primary-200 hover:bg-primary-50/50 transition-all group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                            {complaint.ticket_number}
                          </span>
                          <StatusBadge status={complaint.status} />
                          <PriorityBadge priority={complaint.priority} />
                        </div>
                        <h4 className="font-medium text-neutral-900 group-hover:text-primary-700 transition-colors truncate">
                          {complaint.title}
                        </h4>
                        <div className="flex items-center gap-3 mt-1 text-sm text-neutral-500">
                          <span>{complaint.student?.full_name}</span>
                          <span>•</span>
                          <span>{getCategoryLabel(complaint.category)}</span>
                          <span>•</span>
                          <span>{formatRelativeTime(complaint.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </Card.Content>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <Card className="text-center">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-primary-100 flex items-center justify-center mb-4">
            <UsersIcon className="w-7 h-7 text-primary-600" />
          </div>
          <p className="text-3xl font-bold text-neutral-900">{overview.total_students || 0}</p>
          <p className="text-neutral-500">Total Students</p>
        </Card>

        <Card className="text-center">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-warning-100 flex items-center justify-center mb-4">
            <ExclamationCircleIcon className="w-7 h-7 text-warning-600" />
          </div>
          <p className="text-3xl font-bold text-neutral-900">{overview.unassigned_count || 0}</p>
          <p className="text-neutral-500">Unassigned</p>
        </Card>

        <Card className="text-center">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-success-100 flex items-center justify-center mb-4">
            <ArrowTrendingUpIcon className="w-7 h-7 text-success-600" />
          </div>
          <p className="text-3xl font-bold text-neutral-900">{overview.avg_resolution_time_hours || 0}h</p>
          <p className="text-neutral-500">Avg. Resolution Time</p>
        </Card>
      </div>
    </div>
  );
};

export default AdminDashboard;