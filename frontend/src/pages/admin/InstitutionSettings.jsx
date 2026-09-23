import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BuildingOffice2Icon, ClockIcon, PlusIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select, Textarea } from '../../components/ui/Field';
import Skeleton from '../../components/ui/Skeleton';
import { adminService, errorMessage, fieldErrors } from '../../services/api';
import useAuthStore from '../../stores/authStore';

const TABS = [
  { key: 'profile', label: 'Institution' },
  { key: 'service', label: 'Response times' },
  { key: 'departments', label: 'Departments' },
];

// An institution with no saved matrix keeps the pre-feature behaviour.
// The FUW pilot will deliberately replace these with its approved
// priority timings rather than changing every existing institution by
// migration.
const FALLBACK_PRIORITY_POLICY = {
  low: { acknowledge_hours: 24, resolution_hours: 144, escalation_step_hours: 24 },
  medium: { acknowledge_hours: 24, resolution_hours: 72, escalation_step_hours: 24 },
  high: { acknowledge_hours: 24, resolution_hours: 36, escalation_step_hours: 24 },
  urgent: { acknowledge_hours: 24, resolution_hours: 18, escalation_step_hours: 24 },
};

const PRIORITY_LABELS = { low: 'Low', medium: 'Medium', high: 'High', urgent: 'Urgent' };

export default function InstitutionSettings() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [tab, setTab] = useState('profile');
  const [draft, setDraft] = useState(null);
  const [errors, setErrors] = useState({});
  const [saved, setSaved] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['settings'],
    queryFn: () => adminService.settings(),
    // A platform administrator belongs to no institution, so this asks
    // for something that does not exist. Retrying cannot change that.
    retry: false,
  });

  const { data: departmentData } = useQuery({
    queryKey: ['departments'],
    queryFn: () => adminService.departments(),
  });

  const save = useMutation({
    mutationFn: (payload) => adminService.updateSettings(payload),
    onSuccess: () => {
      setErrors({});
      setSaved('Settings saved.');
      setTimeout(() => setSaved(''), 3000);
      setDraft(null);
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (error) => {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { form: errorMessage(error) });
    },
  });

  // The saved values are the source of truth until a field is edited, so
  // there is no effect copying server state into local state.
  const form = draft ?? data?.institution;

  const set = (field, value) => {
    setDraft({ ...form, [field]: value });
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const setPriority = (priority, field, value) => {
    const policy = form.priority_sla_policy || FALLBACK_PRIORITY_POLICY;
    setDraft({
      ...form,
      priority_sla_policy: {
        ...policy,
        [priority]: { ...policy[priority], [field]: value },
      },
    });
    setErrors((current) => ({
      ...current,
      [`priority_sla_policy.${priority}.${field}`]: undefined,
    }));
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-1 py-3 sm:px-4 sm:py-8">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // These settings belong to one institution, and a platform
  // administrator is attached to none. The request 404s, so the page used
  // to sit on its loading skeleton indefinitely and read as blank. Say so
  // instead, and point at the page that does apply.
  if (!form) {
    const orphaned = user?.role === 'platform_admin' && !user?.institution_id;

    return (
      <div className="mx-auto max-w-3xl px-1 py-3 sm:px-4 sm:py-8">
        <h1 className="font-display text-xl font-semibold tracking-tight text-ink-900 sm:text-2xl">
          Settings
        </h1>
        <div className="mt-4 sm:mt-6 rounded-lg border border-line bg-surface p-3 sm:p-6 shadow-e1">
          <BuildingOffice2Icon className="h-8 w-8 text-ink-400" aria-hidden="true" />
          <p className="mt-3 font-semibold text-ink-900">
            {orphaned
              ? 'Your account is not attached to an institution.'
              : 'We could not load these settings.'}
          </p>
          <p className="mt-1 text-sm text-ink-600">
            {orphaned
              ? 'These settings belong to a single institution. As the platform owner you administer all of them from one place instead.'
              : errorMessage(error)}
          </p>
          {orphaned && (
            <Button className="mt-4" onClick={() => navigate('/platform/institutions')}>
              Go to institutions
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-1 py-3 sm:px-4 sm:py-8">
      <h1 className="font-display text-xl font-semibold tracking-tight text-ink-900 sm:text-2xl">Settings</h1>
      <p className="mt-1 text-ink-600">
        How {form.name} appears, and how quickly complaints must be answered.
      </p>

      <div className="mt-4 sm:mt-6 flex flex-wrap gap-2" role="tablist" aria-label="Settings sections">
        {TABS.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            aria-selected={tab === entry.key}
            onClick={() => setTab(entry.key)}
            className={`min-h-touch rounded-md border px-4 text-sm font-semibold transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700 ${
              tab === entry.key
                ? 'border-brand-700 bg-brand-50 text-brand-800'
                : 'border-line bg-surface text-ink-600 hover:border-brand-600'
            }`}
          >
            {entry.label}
          </button>
        ))}
      </div>

      {saved && (
        <p
          role="status"
          className="mt-4 rounded-md px-4 py-3 text-sm font-medium"
          style={{ backgroundColor: 'var(--status-resolved-bg)', color: 'var(--status-resolved-fg)' }}
        >
          {saved}
        </p>
      )}

      {errors.form && (
        <p
          role="alert"
          className="mt-4 rounded-md px-4 py-3 text-sm font-medium"
          style={{ backgroundColor: 'var(--status-declined-bg)', color: 'var(--status-declined-fg)' }}
        >
          {errors.form}
        </p>
      )}

      {tab === 'profile' && (
        <section className="mt-5 space-y-5 rounded-lg border border-line bg-surface p-3 sm:p-6 shadow-e1">
          <Input
            label="Name"
            required
            value={form.name || ''}
            onChange={(event) => set('name', event.target.value)}
            error={errors.name}
          />
          <div className="grid gap-5 sm:grid-cols-2">
            <Input
              label="Contact email"
              type="email"
              value={form.contact_email || ''}
              onChange={(event) => set('contact_email', event.target.value)}
              hint="Shown to students who need to reach you directly."
            />
            <Input
              label="Contact phone"
              value={form.contact_phone || ''}
              onChange={(event) => set('contact_phone', event.target.value)}
              placeholder="08012345678"
            />
          </div>
          <Input
            label="State"
            value={form.state || ''}
            onChange={(event) => set('state', event.target.value)}
          />
          <Input
            label="Logo URL"
            value={form.logo_url || ''}
            onChange={(event) => set('logo_url', event.target.value)}
            hint="A square image works best."
          />

          <fieldset>
            <legend className="text-sm font-semibold text-ink-700">Anonymous complaints</legend>
            <label className="mt-2 flex min-h-touch items-start gap-3 text-sm">
              <input
                type="checkbox"
                checked={Boolean(form.allow_anonymous)}
                onChange={(event) => set('allow_anonymous', event.target.checked)}
                className="mt-1 h-4 w-4 rounded border-line text-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
              />
              <span className="text-ink-600">
                Let students file without attaching their name. Useful for reports about staff
                conduct, where naming yourself is the reason people stay silent.
              </span>
            </label>
          </fieldset>

          <div className="flex justify-end">
            <Button loading={save.isPending} onClick={() => save.mutate(form)}>
              Save
            </Button>
          </div>
        </section>
      )}

      {tab === 'service' && (
        <section className="mt-5 space-y-5 rounded-lg border border-line bg-surface p-3 sm:p-6 shadow-e1">
          <p className="flex gap-2.5 rounded-md border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-900">
            <ClockIcon className="h-5 w-5 flex-none" aria-hidden="true" />
            <span>
              Deadlines count working hours only. A complaint filed on Friday evening is not due
              over the weekend, and public holidays are skipped.
            </span>
          </p>

          <div className="grid gap-5 sm:grid-cols-2">
            <Input
              label="Hours to acknowledge"
              type="number"
              min="1"
              max="168"
              value={form.acknowledge_sla_hours ?? 24}
              onChange={(event) => set('acknowledge_sla_hours', Number(event.target.value))}
              hint="How quickly someone must confirm they have seen it."
            />
            <Input
              label="Hours to resolve"
              type="number"
              min="1"
              max="720"
              value={form.default_sla_hours ?? 72}
              onChange={(event) => set('default_sla_hours', Number(event.target.value))}
              hint="Urgent halves twice; low doubles."
            />
          </div>

          <div>
            <h2 className="text-sm font-bold text-ink-900">Priority deadlines</h2>
            <p className="mt-1 text-sm text-ink-600">
              A safety report should not wait behind a routine card request. Each row controls
              how quickly it is acknowledged, how the base resolution target is multiplied, and
              how long each escalation rung gets before the next person is told.
            </p>
            <div className="mt-4 overflow-x-auto rounded-md border border-line">
              <table className="w-full min-w-[42rem] text-sm">
                <thead className="bg-canvas text-left text-caption uppercase tracking-wide text-ink-500">
                  <tr>
                    <th className="px-3 py-2">Priority</th>
                    <th className="px-3 py-2">Acknowledge (working hours)</th>
                    <th className="px-3 py-2">Resolve (working hours)</th>
                    <th className="px-3 py-2">Each escalation rung (hours)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {Object.keys(PRIORITY_LABELS).map((priority) => {
                    const policy = form.priority_sla_policy || FALLBACK_PRIORITY_POLICY;
                    const row = policy[priority];
                    return (
                      <tr key={priority}>
                        <td className="px-3 py-3 font-semibold text-ink-900">
                          {PRIORITY_LABELS[priority]}
                        </td>
                        <td className="px-3 py-3">
                          <Input
                            label={`${PRIORITY_LABELS[priority]} acknowledgement hours`}
                            labelHidden
                            className="max-w-28"
                            type="number"
                            min="1"
                            max="720"
                            value={row.acknowledge_hours}
                            onChange={(event) =>
                              setPriority(priority, 'acknowledge_hours', Number(event.target.value))
                            }
                            error={
                              errors[`priority_sla_policy.${priority}.acknowledge_hours`]
                            }
                          />
                        </td>
                        <td className="px-3 py-3">
                          <Input
                            label={`${PRIORITY_LABELS[priority]} resolution hours`}
                            labelHidden
                            className="max-w-28"
                            type="number"
                            min="1"
                            max="1440"
                            value={row.resolution_hours}
                            onChange={(event) =>
                              setPriority(priority, 'resolution_hours', Number(event.target.value))
                            }
                            error={errors[`priority_sla_policy.${priority}.resolution_hours`]}
                          />
                        </td>
                        <td className="px-3 py-3">
                          <Input
                            label={`${PRIORITY_LABELS[priority]} escalation hours`}
                            labelHidden
                            className="max-w-28"
                            type="number"
                            min="1"
                            max="720"
                            value={row.escalation_step_hours}
                            onChange={(event) =>
                              setPriority(
                                priority,
                                'escalation_step_hours',
                                Number(event.target.value),
                              )
                            }
                            error={
                              errors[`priority_sla_policy.${priority}.escalation_step_hours`]
                            }
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <Select
              label="Working day starts"
              value={form.working_hours_start ?? 8}
              onChange={(event) => set('working_hours_start', Number(event.target.value))}
            >
              {Array.from({ length: 13 }, (_, index) => index + 5).map((hour) => (
                <option key={hour} value={hour}>
                  {String(hour).padStart(2, '0')}:00
                </option>
              ))}
            </Select>
            <Select
              label="Working day ends"
              value={form.working_hours_end ?? 17}
              onChange={(event) => set('working_hours_end', Number(event.target.value))}
              error={errors.form && form.working_hours_start >= form.working_hours_end ? ' ' : undefined}
            >
              {Array.from({ length: 13 }, (_, index) => index + 11).map((hour) => (
                <option key={hour} value={hour}>
                  {String(hour).padStart(2, '0')}:00
                </option>
              ))}
            </Select>
          </div>

          <div className="flex justify-end">
            <Button loading={save.isPending} onClick={() => save.mutate(form)}>
              Save
            </Button>
          </div>
        </section>
      )}

      {tab === 'departments' && (
        <DepartmentSettings departments={departmentData?.departments || []} />
      )}
    </div>
  );
}

function DepartmentSettings({ departments }) {
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ name: '', description: '', sla_hours: '' });
  const [error, setError] = useState('');

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['departments'] });

  const create = useMutation({
    mutationFn: () =>
      adminService.createDepartment({
        name: draft.name,
        description: draft.description || undefined,
        sla_hours: draft.sla_hours ? Number(draft.sla_hours) : undefined,
      }),
    onSuccess: () => {
      setDraft({ name: '', description: '', sla_hours: '' });
      setAdding(false);
      setError('');
      refresh();
    },
    onError: (createError) => setError(errorMessage(createError)),
  });

  const toggle = useMutation({
    mutationFn: ({ id, isActive }) => adminService.updateDepartment(id, { is_active: !isActive }),
    onSuccess: refresh,
  });

  return (
    <section className="mt-5 rounded-lg border border-line bg-surface p-3 sm:p-6 shadow-e1">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-ink-900">Departments</h2>
          <p className="mt-0.5 text-caption text-ink-500">
            Complaints are routed to these. A department can set its own resolution target.
          </p>
        </div>
        {!adding && (
          <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
            <PlusIcon className="h-4 w-4" aria-hidden="true" />
            Add
          </Button>
        )}
      </div>

      {adding && (
        <div className="mt-4 space-y-4 rounded-md border border-line bg-canvas p-4">
          <Input
            label="Name"
            required
            value={draft.name}
            onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            placeholder="Examinations"
            error={error}
          />
          <Textarea
            label="What it handles"
            rows={2}
            value={draft.description}
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
          />
          <Input
            label="Resolution target in hours"
            type="number"
            min="1"
            value={draft.sla_hours}
            onChange={(event) => setDraft({ ...draft, sla_hours: event.target.value })}
            hint="Leave blank to use the institution default."
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setAdding(false);
                setError('');
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              loading={create.isPending}
              disabled={draft.name.trim().length < 2}
              onClick={() => create.mutate()}
            >
              Add department
            </Button>
          </div>
        </div>
      )}

      <ul className="mt-4 space-y-2">
        {departments.map((department) => (
          <li
            key={department.id}
            className="flex flex-wrap items-center gap-3 rounded-md border border-line px-4 py-3"
          >
            <BuildingOffice2Icon className="h-5 w-5 flex-none text-ink-500" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="font-medium text-ink-900">{department.name}</p>
              <p className="text-caption text-ink-500">
                {department.description || 'No description'}
                {department.sla_hours && ` · ${department.sla_hours}h target`}
              </p>
            </div>
            <span
              className="rounded-full px-2.5 py-0.5 text-caption font-semibold"
              style={
                department.is_active
                  ? {
                      backgroundColor: 'var(--status-resolved-bg)',
                      color: 'var(--status-resolved-fg)',
                    }
                  : {
                      backgroundColor: 'var(--status-closed-bg)',
                      color: 'var(--status-closed-fg)',
                    }
              }
            >
              {department.is_active ? 'Active' : 'Inactive'}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => toggle.mutate({ id: department.id, isActive: department.is_active })}
            >
              {department.is_active ? 'Deactivate' : 'Activate'}
            </Button>
          </li>
        ))}
        {departments.length === 0 && (
          <li className="rounded-md border border-dashed border-line px-1 py-3 sm:px-4 sm:py-8 text-center text-sm text-ink-500">
            No departments yet. Add one so complaints can be routed.
          </li>
        )}
      </ul>
    </section>
  );
}
