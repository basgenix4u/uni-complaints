/**
 * Application Constants
 */

export const APP_NAME = 'Federal University Wukari';
export const APP_FULL_NAME = 'University Complaints Management System';

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// Complaint Status
export const COMPLAINT_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  RESOLVED: 'resolved',
  CLOSED: 'closed',
  REJECTED: 'rejected',
};

export const STATUS_CONFIG = {
  pending: {
    label: 'Pending',
    color: 'amber',
    bgClass: 'bg-amber-100',
    textClass: 'text-amber-800',
    badgeClass: 'status-pending',
  },
  in_progress: {
    label: 'In Progress',
    color: 'blue',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-800',
    badgeClass: 'status-in-progress',
  },
  resolved: {
    label: 'Resolved',
    color: 'green',
    bgClass: 'bg-green-100',
    textClass: 'text-green-800',
    badgeClass: 'status-resolved',
  },
  closed: {
    label: 'Closed',
    color: 'neutral',
    bgClass: 'bg-neutral-100',
    textClass: 'text-neutral-800',
    badgeClass: 'status-closed',
  },
  rejected: {
    label: 'Rejected',
    color: 'red',
    bgClass: 'bg-red-100',
    textClass: 'text-red-800',
    badgeClass: 'status-rejected',
  },
};

// Complaint Priority
export const PRIORITY_CONFIG = {
  low: {
    label: 'Low',
    color: 'slate',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-700',
    badgeClass: 'priority-low',
  },
  medium: {
    label: 'Medium',
    color: 'blue',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-700',
    badgeClass: 'priority-medium',
  },
  high: {
    label: 'High',
    color: 'orange',
    bgClass: 'bg-orange-100',
    textClass: 'text-orange-700',
    badgeClass: 'priority-high',
  },
  urgent: {
    label: 'Urgent',
    color: 'red',
    bgClass: 'bg-red-100',
    textClass: 'text-red-700',
    badgeClass: 'priority-urgent',
  },
};

// Complaint Categories
export const CATEGORIES = [
  { value: 'transcript', label: 'Transcript Request', icon: '📄' },
  { value: 'registration', label: 'Registration Issues', icon: '📝' },
  { value: 'fees_payment', label: 'Fees & Payment', icon: '💳' },
  { value: 'accommodation', label: 'Accommodation/Hostel', icon: '🏠' },
  { value: 'examination', label: 'Examination Issues', icon: '📋' },
  { value: 'clearance', label: 'Clearance', icon: '✅' },
  { value: 'scholarship', label: 'Scholarship', icon: '🎓' },
  { value: 'library', label: 'Library Services', icon: '📚' },
  { value: 'id_card', label: 'ID Card', icon: '🪪' },
  { value: 'course_registration', label: 'Course Registration', icon: '📖' },
  { value: 'result_issues', label: 'Result Issues', icon: '📊' },
  { value: 'certificate', label: 'Certificate Collection', icon: '🏆' },
  { value: 'admission', label: 'Admission Issues', icon: '🎒' },
  { value: 'transfer', label: 'Transfer Request', icon: '🔄' },
  { value: 'medical', label: 'Medical/Health Services', icon: '🏥' },
  { value: 'security', label: 'Security Issues', icon: '🔒' },
  { value: 'facilities', label: 'Facilities & Maintenance', icon: '🔧' },
  { value: 'academic_advising', label: 'Academic Advising', icon: '👨‍🏫' },
  { value: 'other', label: 'Other', icon: '📌' },
];

// User Roles
export const USER_ROLES = {
  STUDENT: 'student',
  ADMIN: 'admin',
  SUPER_ADMIN: 'super_admin',
};

// Pagination
export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = [5, 10, 20, 50];

// Date Formats
export const DATE_FORMAT = 'MMM dd, yyyy';
export const DATE_TIME_FORMAT = 'MMM dd, yyyy HH:mm';
export const TIME_FORMAT = 'HH:mm';