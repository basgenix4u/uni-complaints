import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';
import { STATUS_CONFIG, PRIORITY_CONFIG, CATEGORIES } from './constants';

/**
 * Format a date string
 * @param {string} dateString - ISO date string
 * @param {string} formatStr - Date format string
 * @returns {string} - Formatted date
 */
export function formatDate(dateString, formatStr = 'MMM dd, yyyy') {
  if (!dateString) return '-';
  
  try {
    const date = parseISO(dateString);
    if (!isValid(date)) return '-';
    return format(date, formatStr);
  } catch {
    return '-';
  }
}

/**
 * Format a date as relative time
 * @param {string} dateString - ISO date string
 * @returns {string} - Relative time string
 */
export function formatRelativeTime(dateString) {
  if (!dateString) return '-';
  
  try {
    const date = parseISO(dateString);
    if (!isValid(date)) return '-';
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return '-';
  }
}

/**
 * Get status configuration
 * @param {string} status - Status value
 * @returns {object} - Status configuration
 */
export function getStatusConfig(status) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.pending;
}

/**
 * Get priority configuration
 * @param {string} priority - Priority value
 * @returns {object} - Priority configuration
 */
export function getPriorityConfig(priority) {
  return PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.medium;
}

/**
 * Get category label
 * @param {string} categoryValue - Category value
 * @returns {string} - Category label
 */
export function getCategoryLabel(categoryValue) {
  const category = CATEGORIES.find((c) => c.value === categoryValue);
  return category ? category.label : categoryValue;
}

/**
 * Get category icon
 * @param {string} categoryValue - Category value
 * @returns {string} - Category emoji icon
 */
export function getCategoryIcon(categoryValue) {
  const category = CATEGORIES.find((c) => c.value === categoryValue);
  return category ? category.icon : '📌';
}

/**
 * Get user initials
 * @param {string} name - Full name
 * @returns {string} - Initials (max 2 characters)
 */
export function getInitials(name) {
  if (!name) return 'U';
  
  const parts = name.trim().split(' ').filter(Boolean);
  if (parts.length === 1) {
    return parts[0].charAt(0).toUpperCase();
  }
  
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} - Truncated text
 */
export function truncateText(text, maxLength = 100) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trim() + '...';
}

/**
 * Format number with commas
 * @param {number} num - Number to format
 * @returns {string} - Formatted number
 */
export function formatNumber(num) {
  if (typeof num !== 'number') return '0';
  return num.toLocaleString();
}

/**
 * Generate a random color class based on string
 * @param {string} str - Input string
 * @returns {string} - Tailwind color class
 */
export function stringToColor(str) {
  if (!str) return 'bg-primary-500';
  
  const colors = [
    'bg-primary-500',
    'bg-secondary-500',
    'bg-accent-500',
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-indigo-500',
    'bg-teal-500',
    'bg-cyan-500',
  ];
  
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  return colors[Math.abs(hash) % colors.length];
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} - Debounced function
 */
export function debounce(func, wait = 300) {
  let timeout;
  
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Check if user is admin
 * @param {object} user - User object
 * @returns {boolean}
 */
export function isAdmin(user) {
  return user?.role === 'admin' || user?.role === 'super_admin';
}

/**
 * Check if user is super admin
 * @param {object} user - User object
 * @returns {boolean}
 */
export function isSuperAdmin(user) {
  return user?.role === 'super_admin';
}

/**
 * Format file size
 * @param {number} bytes - Size in bytes
 * @returns {string} - Formatted size
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>}
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * Calculate percentage
 * @param {number} value - Current value
 * @param {number} total - Total value
 * @returns {number} - Percentage
 */
export function calculatePercentage(value, total) {
  if (!total || total === 0) return 0;
  return Math.round((value / total) * 100);
}