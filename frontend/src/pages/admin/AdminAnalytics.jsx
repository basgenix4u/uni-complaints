import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  UserGroupIcon,
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
  Legend,
  AreaChart,
  Area,
} from 'recharts';
import { Card, Button, Select, Spinner, PageHeader } from '../../components/ui';
import { dashboardService } from '../../services/api';

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const timeRangeOptions = [
  { value: '7', label: 'Last 7 Days' },
  { value: '14', label: 'Last 14 Days' },
  { value: '30', label: 'Last 30 Days' },
  { value: '90', label: 'Last 90 Days' },
];

const AdminAnalytics = () => {
  const [trendDays, setTrendDays] = useState('30');

  // Fetch data
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

  const { data: priorityChartData } = useQuery({
    queryKey: ['priorityChart'],
    queryFn: () => dashboardService.getPriorityChart(),
  });

  const { data: trendChartData } = useQuery({
    queryKey: ['trendChart', trendDays],
    queryFn: () => dashboardService.getTrendChart(parseInt(trendDays)),
  });

  const { data: monthlyChartData } = useQuery({
    queryKey: ['monthlyChart'],
    queryFn: () => dashboardService.getMonthlyChart(),
  });

  const overview = overviewData?.data?.overview || {};
  const statusCounts = overviewData?.data?.status_counts || {};
  const statusChart = statusChartData?.data?.chart_data || [];
  const categoryChart = categoryChartData?.data?.chart_data || [];
  const priorityChart = priorityChartData?.data?.chart_data || [];
  const trendChart = trendChartData?.data?.chart_data || [];
  const monthlyChart = monthlyChartData?.data?.chart_data || [];

  const statCards = [
    {
      title: 'Total Complaints',
      value: overview.total_complaints || 0,
      icon: ChartBarIcon,
      color: 'bg-primary-100 text-primary-600',
    },
    {
      title: 'Resolution Rate',
      value: `${Math.round(((statusCounts.resolved || 0) / (overview.total_complaints || 1)) * 100)}%`,
      icon: ArrowTrendingUpIcon,
      color: 'bg-success-100 text-success-600',
    },
    {
      title: 'Avg. Resolution Time',
      value: `${overview.avg_resolution_time_hours || 0}h`,
      icon: ClockIcon,
      color: 'bg-warning-100 text-warning-600',
    },
    {
      title: 'Total Students',
      value: overview.total_students || 0,
      icon: UserGroupIcon,
      color: 'bg-info-100 text-info-600',
    },
  ];

  if (overviewLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="xl" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics & Reports"
        description="Insights and statistics about complaint management"
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="text-center">
              <div className={`w-14 h-14 mx-auto rounded-2xl flex items-center justify-center mb-4 ${stat.color}`}>
                <stat.icon className="w-7 h-7" />
              </div>
              <p className="text-3xl font-bold text-neutral-900">{stat.value}</p>
              <p className="text-neutral-500">{stat.title}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Trend Chart */}
      <Card>
        <Card.Header>
          <Card.Title>Complaints Trend</Card.Title>
          <Select
            options={timeRangeOptions}
            value={trendDays}
            onChange={setTrendDays}
            className="w-40"
          />
        </Card.Header>
        <Card.Content>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendChart}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
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
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorCount)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card.Content>
      </Card>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <Card>
          <Card.Header>
            <Card.Title>Status Distribution</Card.Title>
          </Card.Header>
          <Card.Content>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusChart}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="count"
                    nameKey="label"
                    label={({ label, percent }) => `${label} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={false}
                  >
                    {statusChart.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card.Content>
        </Card>

        {/* Priority Distribution */}
        <Card>
          <Card.Header>
            <Card.Title>Priority Distribution</Card.Title>
          </Card.Header>
          <Card.Content>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={priorityChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e5e5',
                      borderRadius: '12px',
                    }}
                  />
                  <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                    {priorityChart.map((entry, index) => {
                      const colors = { low: '#64748b', medium: '#3b82f6', high: '#f97316', urgent: '#ef4444' };
                      return <Cell key={`cell-${index}`} fill={colors[entry.priority] || COLORS[index]} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card.Content>
        </Card>
      </div>

      {/* Category Chart */}
      <Card>
        <Card.Header>
          <Card.Title>Complaints by Category</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChart} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={150}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e5e5',
                    borderRadius: '12px',
                  }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card.Content>
      </Card>

      {/* Monthly Chart */}
      <Card>
        <Card.Header>
          <Card.Title>Monthly Complaints ({monthlyChartData?.data?.year})</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e5e5',
                    borderRadius: '12px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#22c55e"
                  strokeWidth={3}
                  dot={{ fill: '#22c55e', strokeWidth: 2, r: 5 }}
                  activeDot={{ r: 8 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card.Content>
      </Card>
    </div>
  );
};

export default AdminAnalytics;