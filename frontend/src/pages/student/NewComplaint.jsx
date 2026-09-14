import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  DocumentTextIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Input, Textarea, PageHeader } from '../../components/ui';
import { studentService } from '../../services/api';
import { CATEGORIES } from '../../utils/constants';

// Validation Schema
const complaintSchema = z.object({
  category: z.string().min(1, 'Please select a category'),
  title: z
    .string()
    .min(1, 'Title is required')
    .min(5, 'Title must be at least 5 characters')
    .max(200, 'Title must be less than 200 characters'),
  description: z
    .string()
    .min(1, 'Description is required')
    .min(20, 'Description must be at least 20 characters')
    .max(5000, 'Description must be less than 5000 characters'),
  priority: z.string().min(1, 'Please select a priority'),
});

const priorityOptions = [
  { value: 'low', label: 'Low - Not urgent, can wait', icon: '🟢' },
  { value: 'medium', label: 'Medium - Should be addressed soon', icon: '🟡' },
  { value: 'high', label: 'High - Needs prompt attention', icon: '🟠' },
  { value: 'urgent', label: 'Urgent - Critical issue', icon: '🔴' },
];

const categoryOptions = CATEGORIES.map(c => ({
  value: c.value,
  label: c.label,
  icon: c.icon,
}));

const NewComplaint = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    getValues,     // <--- Added this
    setError,      // <--- Added this
    clearErrors,   // <--- Added this
    formState: { errors },
  } = useForm({
    resolver: zodResolver(complaintSchema),
    mode: 'onSubmit',
    defaultValues: {
      category: '',
      title: '',
      description: '',
      priority: 'medium',
    },
  });

  const watchCategory = watch('category');
  const watchPriority = watch('priority');
  const watchTitle = watch('title');
  const watchDescription = watch('description');

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: (data) => studentService.createComplaint(data),
    onSuccess: (response) => {
      const ticket = response.data?.complaint?.ticket_number;
      toast.success(
        <div>
          <p className="font-semibold">Complaint submitted successfully!</p>
          <p className="text-sm text-neutral-500">Ticket: {ticket}</p>
        </div>
      );
      navigate('/student/complaints');
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to submit complaint');
    },
  });

  const onSubmit = (data) => {
    submitMutation.mutate(data);
  };

  // FIXED: Manual validation per step to prevent crashing
  const nextStep = () => {
    const data = getValues();

    if (step === 1) {
      // Create a mini-schema just for Step 1
      const step1Schema = complaintSchema.pick({ category: true });
      const result = step1Schema.safeParse(data);

      if (!result.success) {
        // If validation fails, manually set the error so the UI shows it
        setError('category', { message: result.error.errors[0].message });
        return;
      }
      clearErrors('category');
      setStep(2);
    } 
    else if (step === 2) {
      // Create a mini-schema just for Step 2
      const step2Schema = complaintSchema.pick({ title: true, description: true });
      const result = step2Schema.safeParse(data);

      if (!result.success) {
        // Map Zod errors to Form errors
        result.error.errors.forEach((err) => {
          setError(err.path[0], { message: err.message });
        });
        return;
      }
      clearErrors(['title', 'description']);
      setStep(3);
    }
  };

  const prevStep = () => {
    setStep(step - 1);
  };

  const selectedCategory = CATEGORIES.find(c => c.value === watchCategory);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Page Header */}
      <PageHeader
        title="Submit New Complaint"
        description="Fill out the form below to submit your complaint or request"
        breadcrumbs={[
          { label: 'Dashboard', href: '/student/dashboard' },
          { label: 'Complaints', href: '/student/complaints' },
          { label: 'New Complaint' },
        ]}
      />

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {[1, 2, 3].map((s) => (
            <React.Fragment key={s}>
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{
                    scale: step === s ? 1.1 : 1,
                    backgroundColor: step >= s ? '#3b82f6' : '#e5e5e5',
                  }}
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                >
                  {step > s ? (
                    <CheckCircleIcon className="w-6 h-6" />
                  ) : (
                    s
                  )}
                </motion.div>
                <span className={`hidden sm:block text-sm font-medium ${step >= s ? 'text-neutral-900' : 'text-neutral-400'}`}>
                  {s === 1 && 'Category'}
                  {s === 2 && 'Details'}
                  {s === 3 && 'Review'}
                </span>
              </div>
              {s < 3 && (
                <div className={`flex-1 h-1 mx-4 rounded-full ${step > s ? 'bg-primary-500' : 'bg-neutral-200'}`} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Form Card */}
      <Card>
        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Step 1: Category Selection */}
          {step === 1 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <h2 className="text-xl font-semibold text-neutral-900 mb-2">
                What's your complaint about?
              </h2>
              <p className="text-neutral-500 mb-6">
                Select the category that best describes your issue
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {categoryOptions.map((cat) => (
                  <motion.button
                    key={cat.value}
                    type="button"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setValue('category', cat.value);
                      clearErrors('category'); // Clear error immediately on select
                    }}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                      watchCategory === cat.value
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50'
                    }`}
                  >
                    <span className="text-2xl mb-2 block">{cat.icon}</span>
                    <span className={`text-sm font-medium ${watchCategory === cat.value ? 'text-primary-700' : 'text-neutral-700'}`}>
                      {cat.label}
                    </span>
                  </motion.button>
                ))}
              </div>

              {errors.category && (
                <p className="mt-3 text-sm text-danger-600">{errors.category.message}</p>
              )}
            </motion.div>
          )}

          {/* Step 2: Complaint Details */}
          {step === 2 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              <div>
                <h2 className="text-xl font-semibold text-neutral-900 mb-2">
                  Describe your issue
                </h2>
                <p className="text-neutral-500 mb-6">
                  Provide as much detail as possible to help us understand and resolve your issue
                </p>
              </div>

              {/* Selected Category Display */}
              {selectedCategory && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-primary-50 border border-primary-100">
                  <span className="text-2xl">{selectedCategory.icon}</span>
                  <div>
                    <p className="text-xs text-primary-600 font-medium">Category</p>
                    <p className="font-semibold text-primary-900">{selectedCategory.label}</p>
                  </div>
                </div>
              )}

              {/* Title */}
              <Input
                label="Complaint Title"
                placeholder="Brief summary of your issue"
                leftIcon={<DocumentTextIcon className="w-5 h-5" />}
                error={errors.title?.message}
                hint={`${watchTitle?.length || 0}/200 characters`}
                {...register('title')}
              />

              {/* Description */}
              <Textarea
                label="Detailed Description"
                placeholder="Explain your issue in detail. Include relevant dates, names, and any steps you've already taken..."
                rows={6}
                error={errors.description?.message}
                hint={`${watchDescription?.length || 0}/5000 characters (minimum 20)`}
                {...register('description')}
              />

              {/* Priority */}
              <div>
                <label className="label">Priority Level</label>
                <div className="grid grid-cols-2 gap-3">
                  {priorityOptions.map((p) => (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setValue('priority', p.value)}
                      className={`p-3 rounded-xl border-2 text-left transition-all ${
                        watchPriority === p.value
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-neutral-200 hover:border-neutral-300'
                      }`}
                    >
                      <span className="text-lg mr-2">{p.icon}</span>
                      <span className={`text-sm font-medium ${watchPriority === p.value ? 'text-primary-700' : 'text-neutral-700'}`}>
                        {p.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* Step 3: Review */}
          {step === 3 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <h2 className="text-xl font-semibold text-neutral-900 mb-2">
                Review your complaint
              </h2>
              <p className="text-neutral-500 mb-6">
                Please review the details before submitting
              </p>

              <div className="space-y-4">
                {/* Category */}
                <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                  <p className="text-xs text-neutral-500 font-medium mb-1">Category</p>
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{selectedCategory?.icon}</span>
                    <span className="font-semibold text-neutral-900">{selectedCategory?.label}</span>
                  </div>
                </div>

                {/* Title */}
                <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                  <p className="text-xs text-neutral-500 font-medium mb-1">Title</p>
                  <p className="font-semibold text-neutral-900">{watchTitle}</p>
                </div>

                {/* Description */}
                <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                  <p className="text-xs text-neutral-500 font-medium mb-1">Description</p>
                  <p className="text-neutral-700 whitespace-pre-wrap">{watchDescription}</p>
                </div>

                {/* Priority */}
                <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                  <p className="text-xs text-neutral-500 font-medium mb-1">Priority</p>
                  <div className="flex items-center gap-2">
                    <span>{priorityOptions.find(p => p.value === watchPriority)?.icon}</span>
                    <span className="font-semibold text-neutral-900 capitalize">{watchPriority}</span>
                  </div>
                </div>
              </div>

              {/* Warning */}
              <div className="mt-6 p-4 rounded-xl bg-warning-50 border border-warning-200 flex gap-3">
                <ExclamationTriangleIcon className="w-6 h-6 text-warning-600 flex-shrink-0" />
                <div>
                  <p className="font-medium text-warning-800">Before you submit</p>
                  <p className="text-sm text-warning-700">
                    Make sure all information is accurate. You'll receive a ticket number to track your complaint.
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-neutral-100">
            <Button
              type="button"
              variant="ghost"
              onClick={step === 1 ? () => navigate('/student/complaints') : prevStep}
              leftIcon={<ArrowLeftIcon className="w-4 h-4" />}
            >
              {step === 1 ? 'Cancel' : 'Back'}
            </Button>

            {step < 3 ? (
              <Button type="button" onClick={nextStep}>
                Continue
              </Button>
            ) : (
              <Button
                type="submit"
                loading={submitMutation.isPending}
                leftIcon={<CheckCircleIcon className="w-5 h-5" />}
              >
                Submit Complaint
              </Button>
            )}
          </div>
        </form>
      </Card>
    </div>
  );
};

export default NewComplaint;