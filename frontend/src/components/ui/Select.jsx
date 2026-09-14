import React, { Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import { ChevronUpDownIcon, CheckIcon } from '@heroicons/react/24/outline';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '../../utils/cn';

const Select = ({
  label,
  value,
  onChange,
  options = [],
  placeholder = 'Select an option',
  error,
  required = false,
  disabled = false,
  className = '',
}) => {
  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <label className="label">
          {label}
          {required && <span className="text-danger-500 ml-1">*</span>}
        </label>
      )}

      <Listbox value={value} onChange={onChange} disabled={disabled}>
        <div className="relative">
          <Listbox.Button
            className={cn(
              'input text-left flex items-center justify-between',
              error && 'input-error',
              disabled && 'cursor-not-allowed opacity-60',
              !selectedOption && 'text-neutral-400'
            )}
          >
            <span className="block truncate">
              {selectedOption ? selectedOption.label : placeholder}
            </span>
            <ChevronUpDownIcon className="w-5 h-5 text-neutral-400" />
          </Listbox.Button>

          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options
              className="absolute z-50 mt-2 w-full max-h-60 overflow-auto 
                         bg-white rounded-xl shadow-soft-xl border border-neutral-100 
                         py-2 focus:outline-none"
            >
              {options.map((option) => (
                <Listbox.Option
                  key={option.value}
                  value={option.value}
                  className={({ active, selected }) =>
                    cn(
                      'relative cursor-pointer select-none py-2.5 px-4 transition-colors',
                      active && 'bg-primary-50',
                      selected && 'bg-primary-100'
                    )
                  }
                >
                  {({ selected }) => (
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          'block truncate',
                          selected ? 'font-semibold text-primary-700' : 'text-neutral-700'
                        )}
                      >
                        {option.icon && (
                          <span className="mr-2">{option.icon}</span>
                        )}
                        {option.label}
                      </span>
                      {selected && (
                        <CheckIcon className="w-5 h-5 text-primary-600" />
                      )}
                    </div>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>

      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-1.5 text-sm text-danger-600"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Select;