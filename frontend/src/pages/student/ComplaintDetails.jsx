import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  ArrowLeftIcon,
  ClockIcon,
  UserIcon,
  PaperAirplaneIcon,
  DocumentDuplicateIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Textarea, Spinner, Avatar, PageHeader } from '../../components/ui';
import { StatusBadge, PriorityBadge } from '../../components/ui/StatusBadge';
import { studentService } from '../../services/api';
import { formatDate, formatRelativeTime, getCategoryLabel, getCategoryIcon, copyToClipboard } from '../../utils/helpers';
import useAuthStore from '../../stores/authStore';

const ComplaintDetails = () => {
  const { id } = useParams();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  // Fetch complaint details
  const { data, isLoading, error } = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => studentService.getComplaintDetails(id),
  });

  const complaint = data?.data?.complaint;
  const responses = complaint?.responses || [];

  // Add response mutation
  const responseMutation = useMutation({
    mutationFn: (data) => studentService.addResponse(id, data),
    onSuccess: () => {
      toast.success('Response sent successfully');
      reset();
      queryClient.invalidateQueries(['complaint', id]);
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to send response');
    },
  });

  const onSubmit = (data) => {
    if (!data.message?.trim()) return;
    responseMutation.mutate({ message: data.message });
  };

  const handleCopyTicket = async () => {
    const success = await copyToClipboard(complaint.ticket_number);
    if (success) {
      setCopied(true);
      toast.success('Ticket number copied!');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="xl" />
      </div>
    );
  }

  if (error || !complaint) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-semibold text-neutral-900 mb-2">Complaint not found</h2>
        <p className="text-neutral-500 mb-6">The complaint you're looking for doesn't exist or you don't have access.</p>
        <Link to="/student/complaints">
          <Button>Back to Complaints</Button>
        </Link>
      </div>
    );
  }

  const isClosedOrRejected = ['closed', 'rejected'].includes(complaint.status);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back Button */}
      <Link
        to="/student/complaints"
        className="inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6 group"
      >
        <ArrowLeftIcon className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        <span>Back to complaints</span>
      </Link>

      {/* Header Card */}
      <Card className="mb-6">
        <div className="flex flex-col lg:flex-row lg:items-start gap-6">
          {/* Category Icon */}
          <div className="w-16 h-16 rounded-2xl bg-primary-100 flex items-center justify-center text-3xl flex-shrink-0">
            {getCategoryIcon(complaint.category)}
          </div>

          {/* Main Info */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <button
                onClick={handleCopyTicket}
                className="inline-flex items-center gap-1 text-sm font-mono text-primary-600 bg-primary-50 px-3 py-1 rounded-lg hover:bg-primary-100 transition-colors"
              >
                {complaint.ticket_number}
                {copied ? (
                  <CheckIcon className="w-4 h-4 text-success-600" />
                ) : (
                  <DocumentDuplicateIcon className="w-4 h-4" />
                )}
              </button>
              <StatusBadge status={complaint.status} />
              <PriorityBadge priority={complaint.priority} />
            </div>

            <h1 className="text-2xl font-bold text-neutral-900 mb-2">
              {complaint.title}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-500">
              <span className="flex items-center gap-1">
                <ClockIcon className="w-4 h-4" />
                Submitted {formatRelativeTime(complaint.created_at)}
              </span>
              <span>•</span>
              <span>{getCategoryLabel(complaint.category)}</span>
              {complaint.resolved_at && (
                <>
                  <span>•</span>
                  <span className="text-success-600">
                    Resolved {formatRelativeTime(complaint.resolved_at)}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Description */}
        <div className="mt-6 pt-6 border-t border-neutral-100">
          <h3 className="text-sm font-semibold text-neutral-500 uppercase tracking-wider mb-3">
            Description
          </h3>
          <p className="text-neutral-700 whitespace-pre-wrap leading-relaxed">
            {complaint.description}
          </p>
        </div>

        {/* Metadata */}
        <div className="mt-6 pt-6 border-t border-neutral-100 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-neutral-500 mb-1">Status</p>
            <StatusBadge status={complaint.status} />
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">Priority</p>
            <PriorityBadge priority={complaint.priority} />
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">Created</p>
            <p className="text-sm font-medium text-neutral-900">
              {formatDate(complaint.created_at, 'MMM dd, yyyy')}
            </p>
          </div>
          <div>
            <p className="text-xs text-neutral-500 mb-1">Assigned To</p>
            <p className="text-sm font-medium text-neutral-900">
              {complaint.assigned_admin?.full_name || 'Not assigned'}
            </p>
          </div>
        </div>
      </Card>

      {/* Responses Section */}
      <Card>
        <h2 className="text-lg font-semibold text-neutral-900 mb-6">
          Responses ({responses.length})
        </h2>

        {/* Timeline */}
        <div className="space-y-6">
          {responses.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-neutral-500">No responses yet. The admin will respond to your complaint soon.</p>
            </div>
          ) : (
            responses.map((response, index) => {
              const isAdmin = response.author?.role !== 'student';
              const isCurrentUser = response.author?.id === user?.id;

              return (
                <motion.div
                  key={response.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex gap-4 ${isCurrentUser ? 'flex-row-reverse' : ''}`}
                >
                  <Avatar
                    name={response.author?.full_name}
                    size="md"
                    className="flex-shrink-0"
                  />
                  <div className={`flex-1 max-w-[80%] ${isCurrentUser ? 'text-right' : ''}`}>
                    <div
                      className={`inline-block p-4 rounded-2xl ${
                        isCurrentUser
                          ? 'bg-primary-500 text-white rounded-tr-none'
                          : 'bg-neutral-100 text-neutral-900 rounded-tl-none'
                      }`}
                    >
                      <p className="whitespace-pre-wrap text-left">{response.message}</p>
                    </div>
                    <div className={`mt-2 flex items-center gap-2 text-xs text-neutral-400 ${isCurrentUser ? 'justify-end' : ''}`}>
                      <span className="font-medium">
                        {isCurrentUser ? 'You' : response.author?.full_name}
                      </span>
                      {isAdmin && !isCurrentUser && (
                        <span className="px-1.5 py-0.5 bg-primary-100 text-primary-600 rounded text-2xs font-medium">
                          Admin
                        </span>
                      )}
                      <span>•</span>
                      <span>{formatRelativeTime(response.created_at)}</span>
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>

        {/* Reply Form */}
        {!isClosedOrRejected ? (
          <form onSubmit={handleSubmit(onSubmit)} className="mt-8 pt-6 border-t border-neutral-100">
            <Textarea
              placeholder="Type your reply..."
              rows={3}
              error={errors.message?.message}
              {...register('message', { required: 'Please enter a message' })}
            />
            <div className="flex justify-end mt-4">
              <Button
                type="submit"
                loading={responseMutation.isPending}
                rightIcon={<PaperAirplaneIcon className="w-4 h-4" />}
              >
                Send Reply
              </Button>
            </div>
          </form>
        ) : (
          <div className="mt-8 pt-6 border-t border-neutral-100">
            <div className="p-4 rounded-xl bg-neutral-100 text-center">
              <p className="text-neutral-600">
                This complaint is {complaint.status}. No further responses can be added.
              </p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ComplaintDetails;