import React, { Fragment, useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, Transition } from '@headlessui/react';
import {
  Bars3Icon,
  BellIcon,
  MagnifyingGlassIcon,
  UserCircleIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import useAuthStore from '../../stores/authStore';
import Avatar from '../ui/Avatar';

const Navbar = ({ onMenuClick, title }) => {
  const { user, logout, isAdmin } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState('');

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  const profilePath = isAdmin() ? '/admin/settings' : '/student/profile';

  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-neutral-100">
      <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
        {/* Left Section */}
        <div className="flex items-center gap-4">
          {/* Mobile Menu Button */}
          <button
            onClick={onMenuClick}
            className="p-2 rounded-xl text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors lg:hidden"
          >
            <Bars3Icon className="w-6 h-6" />
          </button>

          {/* Page Title */}
          <div className="hidden sm:block">
            <h1 className="text-xl font-semibold text-neutral-900">{title}</h1>
          </div>
        </div>

        {/* Center - Search Bar */}
        <div className="hidden md:flex flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search complaints, tickets..."
              className="w-full pl-11 pr-4 py-2.5 bg-neutral-100 border-0 rounded-xl text-sm placeholder:text-neutral-400 focus:bg-white focus:ring-2 focus:ring-primary-500/20 transition-all"
            />
          </div>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Search Button Mobile */}
          <button className="p-2 rounded-xl text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors md:hidden">
            <MagnifyingGlassIcon className="w-5 h-5" />
          </button>

          {/* Notifications */}
          <Menu as="div" className="relative">
            <Menu.Button className="relative p-2 rounded-xl text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors">
              <BellIcon className="w-5 h-5 sm:w-6 sm:h-6" />
              <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-danger-500 rounded-full ring-2 ring-white" />
            </Menu.Button>

            <Transition
              as={Fragment}
              enter="transition ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="transition ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Menu.Items className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-soft-xl border border-neutral-100 overflow-hidden focus:outline-none">
                <div className="p-4 border-b border-neutral-100">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-neutral-900">Notifications</h3>
                    <span className="badge-primary">3 New</span>
                  </div>
                </div>

                <div className="max-h-80 overflow-y-auto">
                  {[1, 2, 3].map((_, i) => (
                    <Menu.Item key={i}>
                      {({ active }) => (
                        <div
                          className={cn(
                            'p-4 cursor-pointer transition-colors border-b border-neutral-50 last:border-0',
                            active && 'bg-neutral-50'
                          )}
                        >
                          <div className="flex gap-3">
                            <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                              <BellIcon className="w-5 h-5 text-primary-600" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-neutral-900">
                                Your complaint status updated
                              </p>
                              <p className="text-xs text-neutral-500 mt-0.5">
                                Complaint #TKT-2024-ABC123 is now In Progress
                              </p>
                              <p className="text-xs text-neutral-400 mt-1">2 hours ago</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </Menu.Item>
                  ))}
                </div>

                <div className="p-3 bg-neutral-50 border-t border-neutral-100">
                  <Link
                    to={isAdmin() ? '/admin/notifications' : '/student/notifications'}
                    className="block text-center text-sm font-medium text-primary-600 hover:text-primary-700"
                  >
                    View all notifications
                  </Link>
                </div>
              </Menu.Items>
            </Transition>
          </Menu>

          {/* Profile Dropdown */}
          <Menu as="div" className="relative">
            <Menu.Button className="flex items-center gap-3 p-1.5 pr-3 rounded-xl hover:bg-neutral-100 transition-colors">
              <Avatar name={user?.full_name} size="sm" />
              <div className="hidden sm:block text-left">
                <p className="text-sm font-medium text-neutral-900 leading-none">
                  {user?.full_name?.split(' ')[0] || 'User'}
                </p>
                <p className="text-xs text-neutral-500 mt-0.5">
                  {user?.role === 'super_admin' ? 'Super Admin' : user?.role === 'admin' ? 'Admin' : 'Student'}
                </p>
              </div>
            </Menu.Button>

            <Transition
              as={Fragment}
              enter="transition ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="transition ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Menu.Items className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-soft-xl border border-neutral-100 overflow-hidden focus:outline-none">
                <div className="p-4 border-b border-neutral-100">
                  <p className="font-medium text-neutral-900">{user?.full_name}</p>
                  <p className="text-sm text-neutral-500 truncate">{user?.email}</p>
                </div>

                <div className="p-2">
                  <Menu.Item>
                    {({ active }) => (
                      <Link
                        to={profilePath}
                        className={cn(
                          'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors',
                          active ? 'bg-neutral-100 text-neutral-900' : 'text-neutral-600'
                        )}
                      >
                        <UserCircleIcon className="w-5 h-5" />
                        <span>My Profile</span>
                      </Link>
                    )}
                  </Menu.Item>

                  <Menu.Item>
                    {({ active }) => (
                      <Link
                        to={profilePath}
                        className={cn(
                          'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors',
                          active ? 'bg-neutral-100 text-neutral-900' : 'text-neutral-600'
                        )}
                      >
                        <Cog6ToothIcon className="w-5 h-5" />
                        <span>Settings</span>
                      </Link>
                    )}
                  </Menu.Item>

                  <div className="h-px bg-neutral-100 my-2" />

                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={handleLogout}
                        className={cn(
                          'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors',
                          active ? 'bg-danger-50 text-danger-600' : 'text-neutral-600'
                        )}
                      >
                        <ArrowRightOnRectangleIcon className="w-5 h-5" />
                        <span>Logout</span>
                      </button>
                    )}
                  </Menu.Item>
                </div>
              </Menu.Items>
            </Transition>
          </Menu>
        </div>
      </div>
    </header>
  );
};

export default Navbar;