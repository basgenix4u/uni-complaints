import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowPathIcon,
  EnvelopeIcon,
  ExclamationTriangleIcon,
  UserPlusIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select, Textarea } from '../../components/ui/Field';
import Skeleton from '../../components/ui/Skeleton';
import { adminService, errorMessage, invitationService } from '../../services/api';
import useAuthStore from '../../stores/authStore';

/**
 * Getting staff in.
 *
 * Staff are insiders, so self-registration is correctly impossible. The
 * seven endpoints behind this screen have existed since stage 2 with no
 * interface at all, which meant the only way to create an officer was a
 * curl request. Routing complaints to units with nobody in them is not
 * much use, so this is the piece that makes the rest work.
 */
export default function StaffInvitations() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [mode, setMode] = useState('one');
  const [notice, setNotice] = useState('');
  const [problem, setProblem] = useState('');
  const [form, setForm] = useState({ email: '', full_name: '', role: 'officer', department_id: '' });
  const [bulk, setBulk] = useState('');
  const [preview, setPreview] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['invitations'],
    queryFn: () => invitationService.list(),
  });

  const { data: departmentData } = useQuery({
    queryKey: ['departments'],
    queryFn: () => adminService.departments(),
  });

  const { data: health } = useQuery({
    queryKey: ['delivery-health'],
    queryFn: () => adminService.deliveryHealth(),
    enabled: user?.role === 'institution_admin',
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['invitations'] });

  const announce = (message) => {
    setNotice(message);
    setProblem('');
    setTimeout(() => setNotice(''), 4000);
  };

  const invite = useMutation({
    mutationFn: (payload) => invitationService.create(payload),
    onSuccess: () => {
      announce(`Invitation sent to ${form.email}.`);
      setForm({ email: '', full_name: '', role: 'officer', department_id: form.department_id });
      refresh();
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const sendBulk = useMutation({
    mutationFn: ({ csv, dry_run }) => invitationService.bulk({ csv, dry_run }),
    onSuccess: (result, variables) => {
      if (variables.dry_run) {
        setPreview(result.summary);
        setProblem('');
        return;
      }
      setPreview(null);
      setBulk('');
      announce(`${result.summary?.invited ?? 0} invitation(s) sent.`);
      refresh();
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const resend = useMutation({
    mutationFn: (id) => invitationService.resend(id),
    onSuccess: () => {
      announce('Sent again, with a fresh link.');
      refresh();
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const revoke = useMutation({
    mutationFn: (id) => invitationService.revoke(id),
    onSuccess: () => {
      announce('Invitation withdrawn.');
      refresh();
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const units = departmentData?.departments ?? [];
  const invitations = data?.invitations ?? [];
  const pending = invitations.filter((i) => i.status === 'pending');

  // A unit head may only invite into their own unit, so the choice is
  // not offered to them at all.
  const canChooseUnit = user?.role !== 'dept_head';

  const roles =
    user?.role === 'institution_admin' || user?.role === 'platform_admin'
      ? [
          { value: 'officer', label: 'Officer — handles complaints in one unit' },
          { value: 'dept_head', label: 'Unit head — runs a unit and invites its officers' },
          { value: 'dean', label: 'Dean — a faculty, for academic escalations' },
          { value: 'institution_admin', label: 'Administrator — the whole institution' },
        ]
      : [{ value: 'officer', label: 'Officer — handles complaints in one unit' }];

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-1 py-3 sm:px-4 sm:py-8">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-1 py-3 sm:px-4 sm:py-8">
      <h1 className="font-display text-xl font-semibold tracking-tight text-ink-900 sm:text-2xl">
        Invite your staff
      </h1>
      <p className="mt-1 max-w-xl text-ink-600">
        Nobody sets somebody else&apos;s password. An invitation is a single-use link that expires
        after a fortnight, and the recipient chooses their own.
      </p>

      {health?.email?.state === 'not_configured' && (
        <p className="mt-4 flex items-start gap-2.5 rounded-md border border-[#FCD34D] bg-[#FFFBEB] p-4 text-sm text-[#78350F]">
          <ExclamationTriangleIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
          <span>
            <strong className="font-semibold">No email provider is set up.</strong> Invitations
            will be held rather than delivered, and will send once it is configured. Nothing is
            lost in the meantime.
          </span>
        </p>
      )}

      <div aria-live="polite" className="mt-4 empty:mt-0">
        {notice && (
          <p className="rounded-md bg-brand-50 px-4 py-2.5 text-sm font-medium text-brand-800">
            {notice}
          </p>
        )}
        {problem && (
          <p
            role="alert"
            className="rounded-md bg-[#FEF2F2] px-4 py-2.5 text-sm font-medium text-[#B91C1C]"
          >
            {problem}
          </p>
        )}
      </div>

      {/* Bulk import is administrator only on the server, so a unit head
          is not shown a tab that would refuse them. */}
      <div
        className="mt-4 sm:mt-6 flex gap-1 rounded-lg border border-line bg-surface p-1"
        role="tablist"
        hidden={!canChooseUnit}
      >
        {[
          { key: 'one', label: 'One person' },
          { key: 'many', label: 'A whole unit' },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={mode === tab.key}
            onClick={() => setMode(tab.key)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-semibold transition-colors ${
              mode === tab.key ? 'bg-brand-700 text-white' : 'text-ink-600 hover:bg-brand-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {mode === 'one' || !canChooseUnit ? (
        <form
          className="mt-4 space-y-4 rounded-lg border border-line bg-surface p-3 sm:p-5"
          onSubmit={(event) => {
            event.preventDefault();
            invite.mutate({
              ...form,
              department_id: form.department_id || undefined,
            });
          }}
        >
          <Input
            label="Their email"
            type="email"
            placeholder="officer@university.edu.ng"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            required
          />
          <Input
            label="Their name"
            placeholder="So the invitation is not addressed to nobody"
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
          />
          <Select
            label="What they will do"
            value={form.role}
            onChange={(event) => setForm({ ...form, role: event.target.value })}
          >
            {roles.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </Select>

          {canChooseUnit && form.role !== 'institution_admin' && (
            <Select
              label="Which unit"
              value={form.department_id}
              hint="Where their complaints come from. A dean covers a faculty instead."
              onChange={(event) => setForm({ ...form, department_id: event.target.value })}
            >
              <option value="">Choose a unit</option>
              {units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.name}
                </option>
              ))}
            </Select>
          )}

          <Button type="submit" loading={invite.isPending}>
            <UserPlusIcon className="h-5 w-5" aria-hidden="true" />
            Send the invitation
          </Button>
        </form>
      ) : (
        <div className="mt-4 space-y-4 rounded-lg border border-line bg-surface p-3 sm:p-5">
          <Textarea
            label="Paste the list"
            rows={7}
            placeholder={'email,full_name,role\nbursar@uni.edu.ng,Musa Bello,officer'}
            hint="One person per line, with a header row. Checked before anything is sent."
            value={bulk}
            onChange={(event) => {
              setBulk(event.target.value);
              setPreview(null);
            }}
          />

          {preview && (
            <div className="rounded-md border border-line bg-canvas p-4 text-sm">
              <p className="font-semibold text-ink-900">
                {preview.invited ?? 0} to invite, {preview.skipped ?? 0} skipped.
              </p>
              {(preview.problems ?? []).slice(0, 8).map((line) => (
                <p key={line} className="mt-1 text-caption text-[#B45309]">
                  {line}
                </p>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              loading={sendBulk.isPending && !preview}
              onClick={() => sendBulk.mutate({ csv: bulk, dry_run: true })}
            >
              Check the list first
            </Button>
            <Button
              disabled={!preview || !(preview.invited > 0)}
              loading={sendBulk.isPending && Boolean(preview)}
              onClick={() => sendBulk.mutate({ csv: bulk, dry_run: false })}
            >
              Send {preview?.invited ? `${preview.invited} ` : ''}invitations
            </Button>
          </div>
        </div>
      )}

      <h2 className="mt-6 sm:mt-8 font-display text-lg font-semibold text-ink-900">
        Waiting to be accepted
      </h2>

      {pending.length === 0 ? (
        <p className="mt-2 rounded-lg border border-line bg-surface p-3 sm:p-5 text-sm text-ink-600">
          Nothing outstanding. Everyone invited has either joined or been withdrawn.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {pending.map((invitation) => (
            <li
              key={invitation.id}
              className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface p-3 sm:p-4"
            >
              <EnvelopeIcon className="h-5 w-5 shrink-0 text-ink-500" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-ink-900">
                  {invitation.full_name || invitation.email}
                </p>
                <p className="text-caption text-ink-500">
                  {invitation.email} · {(invitation.role || '').replace('_', ' ')}
                  {invitation.department ? ` · ${invitation.department}` : ''}
                  {invitation.sent_count > 1 ? ` · sent ${invitation.sent_count} times` : ''}
                </p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                loading={resend.isPending}
                onClick={() => resend.mutate(invitation.id)}
              >
                <ArrowPathIcon className="h-4 w-4" aria-hidden="true" />
                Send again
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => revoke.mutate(invitation.id)}
              >
                <XMarkIcon className="h-4 w-4" aria-hidden="true" />
                Withdraw
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
