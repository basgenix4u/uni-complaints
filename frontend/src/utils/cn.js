import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combines class names using clsx and merges Tailwind classes
 * @param  {...any} inputs - Class names to combine
 * @returns {string} - Combined class names
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}