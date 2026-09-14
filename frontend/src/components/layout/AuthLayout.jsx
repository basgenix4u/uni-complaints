import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const AuthLayout = () => {
  return (
    <div className="min-h-screen flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0 bg-grid" />
        </div>
        
        {/* Floating Shapes */}
        <motion.div
          animate={{
            y: [0, -20, 0],
            rotate: [0, 5, 0],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute top-20 left-20 w-32 h-32 rounded-3xl bg-white/10 backdrop-blur-sm"
        />
        <motion.div
          animate={{
            y: [0, 20, 0],
            rotate: [0, -5, 0],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute bottom-32 right-20 w-40 h-40 rounded-full bg-white/10 backdrop-blur-sm"
        />
        <motion.div
          animate={{
            y: [0, -15, 0],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute top-1/2 left-1/3 w-24 h-24 rounded-2xl bg-white/5 backdrop-blur-sm"
        />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-12 xl:px-20">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 mb-12">
            <div className="w-14 h-14 rounded-2xl bg-white flex items-center justify-center shadow-2xl">
              <span className="text-primary-600 font-bold text-2xl">U</span>
            </div>
            <div>
              <h1 className="text-white font-bold text-2xl">UniComplaint</h1>
              <p className="text-primary-200 text-sm">Student Complaint System</p>
            </div>
          </Link>

          {/* Hero Text */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="text-4xl xl:text-5xl font-bold text-white leading-tight mb-6">
              Streamline Your
              <br />
              <span className="text-primary-200">University Experience</span>
            </h2>
            <p className="text-primary-100 text-lg max-w-md leading-relaxed">
              Submit complaints, track requests, and get faster resolutions. 
              Your voice matters, and we're here to help.
            </p>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex gap-12 mt-12"
          >
            <div>
              <p className="text-4xl font-bold text-white">10K+</p>
              <p className="text-primary-200 text-sm">Complaints Resolved</p>
            </div>
            <div>
              <p className="text-4xl font-bold text-white">98%</p>
              <p className="text-primary-200 text-sm">Satisfaction Rate</p>
            </div>
            <div>
              <p className="text-4xl font-bold text-white">24h</p>
              <p className="text-primary-200 text-sm">Avg. Response Time</p>
            </div>
          </motion.div>

          {/* Testimonial */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="mt-12 p-6 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/20"
          >
            <p className="text-white/90 italic mb-4">
              "This system has transformed how we handle student complaints. 
              The response time has improved by 70%!"
            </p>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary-300 flex items-center justify-center text-primary-700 font-semibold">
                D
              </div>
              <div>
                <p className="text-white font-medium text-sm">Dr. Adebayo</p>
                <p className="text-primary-200 text-xs">Dean of Student Affairs</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12 bg-white">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/30">
                <span className="text-white font-bold text-xl">U</span>
              </div>
              <div>
                <h1 className="font-bold text-neutral-900 text-xl">UniComplaint</h1>
                <p className="text-xs text-neutral-500">Management System</p>
              </div>
            </Link>
          </div>

          {/* Form Content */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <Outlet />
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;