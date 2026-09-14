import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
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
  PencilIcon,
  UserPlusIcon,
  FlagIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Textarea, Select, Spinner, Avatar, Modal } from '../../components/ui';
import { StatusBadge, PriorityBadge } from '../../components/ui/StatusBadge';
import { adminService } from '../../services/api';
import { formatDate, formatRelativeTime, getCategoryLabel, getCategoryIcon, copyToClipboard } from '../../utils/helpers';
import useAuthStore from '../../stores/authStore';

const statusOptions = [
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
  { value: 'rejected', label: 'Rejected' },
];

const priorityOptions = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
];

const AdminComplaintDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  
  const [copied, setCopied] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showPriorityModal, setShowPriorityModal] = useState(false);
  const [isInternalNote, setIsInternalNote] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  // Fetch complaint details
  const { data, isLoading, error } = useQuery({
    queryKey: ['adminComplaint', id],
    queryFn: () => adminService.getComplaintDetails(id),
  });

  // Fetch admin list for assignment
  const { data: adminListData } = useQuery({
    queryKey: ['adminList'],
    queryFn: () => adminService.getAdminList(),
  });

  const complaint = data?.data?.complaint;
  const responses = complaint?.responses || [];
  const adminList = adminListData?.data?.admins || [];

  // Mutations
  const updateStatusMutation = useMutation({
    mutationFn: (data) => adminService.updateStatus(id, data),
    onSuccess: () => {
      toast.success('Status updated successfully');
      setShowStatusModal(false);
      queryClient.invalidateQueries(['adminComplaint', id]);
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to update status');
    },
  });

  const updatePriorityMutation = useMutation({
    mutationFn: (data) => adminService.updatePriority(id, data),
    onSuccess: () => {
      toast.success('Priority updated successfully');
      setShowPriorityModal(false);
      queryClient.invalidateQueries(['adminComplaint', id]);
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to update priority');
    },
  });

  const assignMutation = useMutation({
    mutationFn: (data) => adminService.assignComplaint(id, data),
    onSuccess: () => {
      toast.success('Complaint assigned successfully');
      setShowAssignModal(false);
      queryClient.invalidateQueries(['adminComplaint', id]);
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to assign complaint');
    },
  });

  const responseMutation = useMutation({
    mutationFn: (data) => adminService.addResponse(id, data),
    onSuccess: () => {
      toast.success(isInternalNote ? 'Internal note added' : 'Response sent successfully');
      reset();
      setIsInternalNote(false);
      queryClient.invalidateQueries(['adminComplaint', id]);
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to send response');
    },
  });

  const handleCopyTicket = async () => {
    const success = await copyToClipboard(complaint.ticket_number);
    if (success) {
      setCopied(true);
      toast.success('Ticket number copied!');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const onSubmitResponse = (data) => {
    if (!data.message?.trim()) return;
    responseMutation.mutate({ message: data.message, is_internal: isInternalNote });
  };

  const handleStatusChange = (status, comment) => {
    updateStatusMutation.mutate({ status, comment });
  };

  const handlePriorityChange = (priority) => {
    updatePriorityMutation.mutate({ priority });
  };

  const handleAssign = (adminId) => {
    assignMutation.mutate({ admin_id: adminId || null });
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
        <p className="text-neutral-500 mb-6">The complaint you're looking for doesn't exist.</p>
        <Link to="/admin/complaints">
          <Button>Back to Complaints</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Back Button */}
      <Link
        to="/admin/complaints"
        className="inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6 group"
      >
        <ArrowLeftIcon className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        <span>Back to complaints</span>
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header Card */}
          <Card>
            <div className="flex flex-col sm:flex-row sm:items-start gap-4">
              <div className="w-14 h-14 rounded-2xl bg-primary-100 flex items-center justify-center text-2xl flex-shrink-0">
                {getCategoryIcon(complaint.category)}
              </div>

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
                </div>

                <h1 className="text-xl font-bold text-neutral-900 mb-2">
                  {complaint.title}
                </h1>

                <div className="flex flex-wrap items-center gap-3 text-sm text-neutral-500">
                  <span className="flex items-center gap-1">
                    <ClockIcon className="w-4 h-4" />
                    {formatRelativeTime(complaint.created_at)}
                  </span>
                  <span>•</span>
                  <span>{getCategoryLabel(complaint.category)}</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-neutral-100">
              <h3 className="text-sm font-semibold text-neutral-500 uppercase tracking-wider mb-3">
                Description
              </h3>
              <p className="text-neutral-700 whitespace-pre-wrap leading-relaxed">
                {complaint.description}
              </p>
            </div>

            {/* Admin Notes */}
            {complaint.admin_notes && (
              <div className="mt-6 pt-6 border-t border-neutral-100">
                <h3 className="text-sm font-semibold text-warning-600 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <ExclamationTriangleIcon className="w-4 h-4" />
                  Internal Admin Notes
                </h3>
                <p className="text-neutral-700 whitespace-pre-wrap bg-warning-50 p-4 rounded-xl border border-warning-100">
                  {complaint.admin_notes}
                </p>
              </div>
            )}
          </Card>

          {/* Responses Section */}
          <Card>
            <h2 className="text-lg font-semibold text-neutral-900 mb-6">
              Conversation ({responses.length})
            </h2>

            <div className="space-y-6">
              {responses.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-neutral-500">No responses yet. Be the first to respond.</p>
                </div>
              ) : (
                responses.map((response, index) => {
                  const isAdmin = response.author?.role !== 'student';
                  const isInternal = response.is_internal;

                  return (
                    <motion.div
                      key={response.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={`flex gap-4 ${isAdmin ? 'flex-row-reverse' : ''}`}
                    >
                      <Avatar
                        name={response.author?.full_name}
                        size="md"
                        className="flex-shrink-0"
                      />
                      <div className={`flex-1 max-w-[80%] ${isAdmin ? 'text-right' : ''}`}>
                        <div
                          className={`inline-block p-4 rounded-2xl ${
                            isInternal
                              ? 'bg-warning-100 text-warning-900 border border-warning-200 rounded-tr-none'
                              : isAdmin
                              ? 'bg-primary-500 text-white rounded-tr-none'
                              : 'bg-neutral-100 text-neutral-900 rounded-tl-none'
                          }`}
                        >
                          {isInternal && (
                            <p className="text-xs font-semibold text-warning-700 mb-2 flex items-center gap-1 justify-end">
                              <ExclamationTriangleIcon className="w-3 h-3" />
                              Internal Note
                            </p>
                          )}
                          <p className="whitespace-pre-wrap text-left">{response.message}</p>
                        </div>
                        <div className={`mt-2 flex items-center gap-2 text-xs text-neutral-400 ${isAdmin ? 'justify-end' : ''}`}>
                          <span className="font-medium">{response.author?.full_name}</span>
                          {isAdmin && (
                            <span className="px-1.5 py-0.5 bg-primary-100 text-primary-600 rounded text-2xs font-medium">
                              {response.author?.role === 'super_admin' ? 'Super Admin' : 'Admin'}
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
            <form onSubmit={handleSubmit(onSubmitResponse)} className="mt-8 pt-6 border-t border-neutral-100">
              <div className="flex items-center gap-4 mb-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isInternalNote}
                    onChange={(e) => setIsInternalNote(e.target.checked)}
                    className="w-4 h-4 rounded border-neutral-300 text-warning-600 focus:ring-warning-500"
                  />
                  <span className="text-sm text-neutral-600">Internal note (visible to admins only)</span>
                </label>
              </div>

              <Textarea
                placeholder={isInternalNote ? "Add an internal note..." : "Type your response to the student..."}
                rows={3}
                error={errors.message?.message}
                className={isInternalNote ? 'border-warning-300 focus:border-warning-500' : ''}
                {...register('message', { required: 'Please enter a message' })}
              />
              
              <div className="flex justify-end mt-4">
                <Button
                  type="submit"
                  loading={responseMutation.isPending}
                  variant={isInternalNote ? 'warning' : 'primary'}
                  rightIcon={<PaperAirplaneIcon className="w-4 h-4" />}
                >
                  {isInternalNote ? 'Add Note' : 'Send Response'}
                </Button>
              </div>
            </form>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status Card */}
          <Card>
            <h3 className="font-semibold text-neutral-900 mb-4">Status</h3>
            <div className="flex items-center justify-between">
              <StatusBadge status={complaint.status} />
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<PencilIcon className="w-4 h-4" />}
                onClick={() => setShowStatusModal(true)}
              >
                Change
              </Button>
            </div>
          </Card>

          {/* Priority Card */}
          <Card>
            <h3 className="font-semibold text-neutral-900 mb-4">Priority</h3>
            <div className="flex items-center justify-between">
              <PriorityBadge priority={complaint.priority} />
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<FlagIcon className="w-4 h-4" />}
                onClick={() => setShowPriorityModal(true)}
              >
                Change
              </Button>
            </div>
          </Card>

          {/* Assignment Card */}
          <Card>
            <h3 className="font-semibold text-neutral-900 mb-4">Assigned To</h3>
            <div className="flex items-center justify-between">
              {complaint.assigned_admin ? (
                <div className="flex items-center gap-3">
                  <Avatar name={complaint.assigned_admin.full_name} size="sm" />
                  <span className="text-sm font-medium">{complaint.assigned_admin.full_name}</span>
                </div>
              ) : (
                <span className="text-sm text-neutral-400">Not assigned</span>
              )}
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<UserPlusIcon className="w-4 h-4" />}
                onClick={() => setShowAssignModal(true)}
              >
                {complaint.assigned_admin ? 'Reassign' : 'Assign'}
              </Button>
            </div>
          </Card>

          {/* Student Info Card */}
          <Card>
            <h3 className="font-semibold text-neutral-900 mb-4">Student Information</h3>
            <div className="flex items-center gap-3 mb-4">
              <Avatar name={complaint.student?.full_name} size="lg" />
              <div>
                <p className="font-semibold text-neutral-900">{complaint.student?.full_name}</p>
                <p className="text-sm text-neutral-500">{complaint.student?.matric_number}</p>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-neutral-500">Email</span>
                <span className="text-neutral-900">{complaint.student?.email}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-500">Department</span>
                <span className="text-neutral-900">{complaint.student?.department || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-500">Faculty</span>
                <span className="text-neutral-900">{complaint.student?.faculty || 'N/A'}</span>
              </div>
            </div>
          </Card>

          {/* Timeline Card */}
          <Card>
            <h3 className="font-semibold text-neutral-900 mb-4">Timeline</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-neutral-500">Created</span>
                <span className="text-neutral-900">{formatDate(complaint.created_at, 'MMM dd, yyyy HH:mm')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-500">Last Updated</span>
                <span className="text-neutral-900">{formatDate(complaint.updated_at, 'MMM dd, yyyy HH:mm')}</span>
              </div>
              {complaint.resolved_at && (
                <div className="flex justify-between">
                  <span className="text-neutral-500">Resolved</span>
                  <span className="text-success-600">{formatDate(complaint.resolved_at, 'MMM dd, yyyy HH:mm')}</span>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Status Change Modal */}
      <StatusChangeModal
        isOpen={showStatusModal}
        onClose={() => setShowStatusModal(false)}
        currentStatus={complaint.status}
        onSubmit={handleStatusChange}
        isLoading={updateStatusMutation.isPending}
      />

      {/* Priority Change Modal */}
      <PriorityChangeModal
        isOpen={showPriorityModal}
        onClose={() => setShowPriorityModal(false)}
        currentPriority={complaint.priority}
        onSubmit={handlePriorityChange}
        isLoading={updatePriorityMutation.isPending}
      />

      {/* Assign Modal */}
      <AssignModal
        isOpen={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        admins={adminList}
        currentAssignee={complaint.assigned_to}
        onSubmit={handleAssign}
        isLoading={assignMutation.isPending}
      />
    </div>
  );
};

// Status Change Modal Component
const StatusChangeModal = ({ isOpen, onClose, currentStatus, onSubmit, isLoading }) => {
  const [status, setStatus] = useState(currentStatus);
  const [comment, setComment] = useState('');

  const handleSubmit = () => {
    onSubmit(status, comment);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Update Status" size="md">
      <div className="space-y-4">
        <Select
          label="New Status"
          options={statusOptions}
          value={status}
          onChange={setStatus}
        />
        <Textarea
          label="Comment (Optional)"
          placeholder="Add a comment about this status change..."
          rows={3}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
      </div>
      <Modal.Footer>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={handleSubmit} loading={isLoading}>Update Status</Button>
      </Modal.Footer>
    </Modal>
  );
};

// Priority Change Modal Component
const PriorityChangeModal = ({ isOpen, onClose, currentPriority, onSubmit, isLoading }) => {
  const [priority, setPriority] = useState(currentPriority);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Update Priority" size="sm">
      <div className="space-y-3">
        {priorityOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setPriority(option.value)}
            className={`w-full p-3 rounded-xl border-2 text-left transition-all ${
              priority === option.value
                ? 'border-primary-500 bg-primary-50'
                : 'border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <PriorityBadge priority={option.value} />
          </button>
        ))}
      </div>
      <Modal.Footer>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={() => onSubmit(priority)} loading={isLoading}>Update Priority</Button>
      </Modal.Footer>
    </Modal>
  );
};

// Assign Modal Component
const AssignModal = ({ isOpen, onClose, admins, currentAssignee, onSubmit, isLoading }) => {
  const [selectedAdmin, setSelectedAdmin] = useState(currentAssignee);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Assign Complaint" size="md">
      <div className="space-y-3">
        <button
          type="button"
          onClick={() => setSelectedAdmin(null)}
          className={`w-full p-3 rounded-xl border-2 text-left transition-all ${
            selectedAdmin === null
              ? 'border-primary-500 bg-primary-50'
              : 'border-neutral-200 hover:border-neutral-300'
          }`}
        >
          <span className="text-neutral-600">Unassigned</span>
        </button>
        
        {admins.map((admin) => (
          <button
            key={admin.id}
            type="button"
            onClick={() => setSelectedAdmin(admin.id)}
            className={`w-full p-3 rounded-xl border-2 text-left transition-all flex items-center gap-3 ${
              selectedAdmin === admin.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <Avatar name={admin.full_name} size="sm" />
            <div>
              <p className="font-medium text-neutral-900">{admin.full_name}</p>
              <p className="text-xs text-neutral-500">{admin.email}</p>
            </div>
          </button>
        ))}
      </div>
      <Modal.Footer>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={() => onSubmit(selectedAdmin)} loading={isLoading}>
          {selectedAdmin ? 'Assign' : 'Unassign'}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default AdminComplaintDetails;