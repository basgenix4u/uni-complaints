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
              <h1 className="text-white font-bold text-2xl">Resolve</h1>
              <p className="text-primary-200 text-sm">Complaints that reach someone</p>
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

          {/* What the product actually promises. The figures that were
              here before -- 10K+ resolved, 98% satisfaction, a testimonial
              from a Dean -- were invented. Nobody has used this yet, and
              inventing evidence on a complaints system is precisely the
              dishonesty it exists to address. */}
          <motion.ul
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-12 space-y-4"
          >
            {[
              ['A ticket, immediately', 'Track it without signing in. Nothing gets lost in an inbox.'],
              ['A named deadline', 'Counted in working hours, and escalated up the chain if it passes.'],
              ['The right office', 'Your complaint is routed on submission. You need not know who handles what.'],
            ].map(([title, detail]) => (
              <li key={title} className="flex gap-3">
                <span
                  aria-hidden="true"
                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-white/70"
                />
                <span>
                  <span className="block font-semibold text-white">{title}</span>
                  <span className="block text-sm text-primary-200">{detail}</span>
                </span>
              </li>
            ))}
          </motion.ul>

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
                <h1 className="font-bold text-neutral-900 text-xl">Resolve</h1>
                <p className="text-xs text-neutral-500">Complaint resolution</p>
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