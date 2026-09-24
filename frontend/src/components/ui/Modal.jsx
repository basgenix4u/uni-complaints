import React, { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { cn } from '../../utils/cn';

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '3xl': 'max-w-3xl',
  '4xl': 'max-w-4xl',
  full: 'max-w-full mx-4',
};

const Modal = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'md',
  showCloseButton = true,
  closeOnOverlayClick = true,
  className = '',
}) => {
  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-50"
        onClose={closeOnOverlayClick ? onClose : () => {}}
      >
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel
                className={cn(
                  'flex max-h-[calc(100dvh-2rem)] w-full transform flex-col overflow-hidden rounded-xl bg-surface shadow-e4 transition-all sm:rounded-2xl',
                  sizeClasses[size],
                  className
                )}
              >
                {(title || showCloseButton) && (
                  <div className="flex flex-none items-start justify-between gap-4 border-b border-line p-4 sm:p-6">
                    <div>
                      {title && (
                        <Dialog.Title className="text-xl font-semibold text-neutral-900">
                          {title}
                        </Dialog.Title>
                      )}
                      {description && (
                        <Dialog.Description className="mt-1 text-sm text-neutral-500">
                          {description}
                        </Dialog.Description>
                      )}
                    </div>

                    {showCloseButton && (
                      <button
                        type="button"
                        onClick={onClose}
                        className="-mr-2 -mt-2 inline-flex min-h-touch min-w-touch items-center justify-center rounded-md text-ink-500 transition-colors hover:bg-canvas hover:text-ink-900"
                      >
                        <XMarkIcon className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                )}

                <div className="min-h-0 overflow-y-auto p-4 sm:p-6">{children}</div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};

const ModalFooter = ({ children, className = '' }) => (
  <div
    className={cn(
      'flex items-center justify-end gap-3 mt-6 pt-4 border-t border-neutral-100',
      className
    )}
  >
    {children}
  </div>
);

Modal.Footer = ModalFooter;

export default Modal;