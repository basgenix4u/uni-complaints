import React from 'react';
import { motion } from 'framer-motion';

const PageHeader = ({
  title,
  description,
  action,
  breadcrumbs,
  className = '',
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`mb-8 ${className}`}
    >
      {breadcrumbs && (
        <nav className="flex mb-4" aria-label="Breadcrumb">
          <ol className="inline-flex items-center space-x-1 md:space-x-3">
            {breadcrumbs.map((item, index) => (
              <li key={index} className="inline-flex items-center">
                {index > 0 && (
                  <svg
                    className="w-4 h-4 mx-2 text-neutral-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
                {item.href ? (
                  <a
                    href={item.href}
                    className="text-sm font-medium text-neutral-500 hover:text-neutral-700"
                  >
                    {item.label}
                  </a>
                ) : (
                  <span className="text-sm font-medium text-neutral-900">
                    {item.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900 font-display">
            {title}
          </h1>
          {description && (
            <p className="text-neutral-500 mt-1">{description}</p>
          )}
        </div>

        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
    </motion.div>
  );
};

export default PageHeader;