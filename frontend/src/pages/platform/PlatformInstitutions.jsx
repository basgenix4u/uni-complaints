import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BuildingLibraryIcon, PlusIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/Field';
import Skeleton from '../../components/ui/Skeleton';
import { errorMessage, fieldErrors, platformService } from '../../services/api';
import { formatDate } from '../../utils/format';

const TYPES = [
  { value: 'university', label: 'University' },
  { value: 'polytechnic', label: 'Polytechnic' },
  { value: 'college', label: 'College of education' },
  { value: 'hospital', label: 'Teaching hospital' },
  { value: 'agency', label: 'Government agency' },
];

const EMPTY = {
  name: '',
  code: '',
  slug: '',
  type: 'university',
  state: '',
  admin_name: '',
  admin_email: '',
  admin_password: '',
};

/** Derives a URL-safe slug from the institution name. */
const toSlug = (value) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');

/** Suggests a ticket prefix from the initials of the name. */
const toCode = (value) =>
  value
    .split(/\s+/)
    .filter((word) => word.length > 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 4);

export default function PlatformInstitutions() {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [created, setCreated] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['platform-institutions'],
    queryFn: () => platformService.institutions(),
  });

  const { data: statsData } = useQuery({
    queryKey: ['platform-stats'],
    queryFn: () => platformService.stats(),
  });

  const institutions = data?.institutions || [];
  const stats = statsData?.stats || {};

  const create = useMutation({
    mutationFn: () => platformService.createInstitution(form),
    onSuccess: (result) => {
      setCreated(result);
      setForm(EMPTY);
      setCreating(false);
      setErrors({});
      queryClient.invalidateQueries({ queryKey: ['platform-institutions'] });
      queryClient.invalidateQueries({ queryKey: ['platform-stats'] });
    },
    onError: (error) => {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { form: errorMessage(error) });
    },
  });

  const toggle = useMutation({
    mutationFn: (id) => platformService.toggleInstitution(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['platform-institutions'] }),
  });

  // Name drives the slug and ticket prefix until either is edited by hand.
  const setName = (value) => {
    setForm((current) => ({
      ...current,
      name: value,
      slug: current.slug === toSlug(current.name) ? toSlug(value) : current.slug,
      code: current.code === toCode(current.name) ? toCode(value) : current.code,
    }));
  };

  const set = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900">
            Institutions
          </h1>
          <p className="mt-1 text-ink-600">Every organisation using this deployment.</p>
        </div>
        {!creating && (
          <Button onClick={() => setCreating(true)}>
            <PlusIcon className="h-5 w-5" aria-hidden="true" />
            Add an institution
          </Button>
        )}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Institutions" value={stats.institutions} />
        <Stat label="Active" value={stats.active_institutions} />
        <Stat label="Users" value={stats.users} />
        <Stat label="Complaints" value={stats.complaints} />
      </div>

      {created && (
        <section
          className="mt-6 rounded-lg p-6"
          style={{ backgroundColor: 'var(--status-resolved-bg)', color: 'var(--status-resolved-fg)' }}
        >
          <h2 className="font-display text-lg font-semibold">
            {created.institution.name} is ready
          </h2>
          <p className="mt-1 text-sm">
            Default departments have been created. Give these details to their administrator, who
            should change the password on first sign in.
          </p>
          <dl className="mt-4 space-y-1.5 text-sm">
            <Pair label="Sign-in address" value={created.institution.slug} />
            <Pair label="Administrator" value={created.admin.email} />
            <Pair label="Ticket prefix" value={`${created.institution.code}-XXXX-0001`} mono />
          </dl>
          <Button
            variant="secondary"
            size="sm"
            className="mt-4"
            onClick={() => setCreated(null)}
          >
            Done
          </Button>
        </section>
      )}

      {creating && (
        <section className="mt-6 space-y-5 rounded-lg border border-line bg-surface p-6 shadow-e1">
          <h2 className="text-sm font-bold text-ink-900">New institution</h2>

          {errors.form && (
            <p
              role="alert"
              className="rounded-md px-4 py-3 text-sm font-medium"
              style={{
                backgroundColor: 'var(--status-declined-bg)',
                color: 'var(--status-declined-fg)',
              }}
            >
              {errors.form}
            </p>
          )}

          <Input
            label="Name"
            required
            value={form.name}
            onChange={(event) => setName(event.target.value)}
            error={errors.name}
            placeholder="Federal Polytechnic Bauchi"
          />

          <div className="grid gap-5 sm:grid-cols-2">
            <Input
              label="Ticket prefix"
              required
              value={form.code}
              onChange={(event) => set('code', event.target.value.toUpperCase())}
              error={errors.code}
              hint="2 to 8 capitals. Appears on every ticket."
              className="font-mono"
              maxLength={8}
            />
            <Input
              label="Sign-in address"
              required
              value={form.slug}
              onChange={(event) => set('slug', toSlug(event.target.value))}
              error={errors.slug}
              hint="Lower case, hyphens between words."
              className="font-mono"
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <Select label="Type" value={form.type} onChange={(event) => set('type', event.target.value)}>
              {TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </Select>
            <Input
              label="State"
              value={form.state}
              onChange={(event) => set('state', event.target.value)}
              placeholder="Bauchi"
            />
          </div>

          <div className="border-t border-line pt-5">
            <h3 className="text-sm font-bold text-ink-900">Their first administrator</h3>
            <p className="mt-0.5 text-caption text-ink-500">
              Created together with the institution, since staff accounts can only be made by an
              existing administrator.
            </p>

            <div className="mt-4 space-y-5">
              <Input
                label="Full name"
                required
                value={form.admin_name}
                onChange={(event) => set('admin_name', event.target.value)}
                error={errors.admin_name}
              />
              <div className="grid gap-5 sm:grid-cols-2">
                <Input
                  label="Email"
                  type="email"
                  required
                  value={form.admin_email}
                  onChange={(event) => set('admin_email', event.target.value)}
                  error={errors.admin_email}
                />
                <Input
                  label="Temporary password"
                  type="text"
                  required
                  value={form.admin_password}
                  onChange={(event) => set('admin_password', event.target.value)}
                  error={errors.admin_password}
                  hint="At least 8 characters, with a capital, a small letter and a number."
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                setCreating(false);
                setErrors({});
              }}
            >
              Cancel
            </Button>
            <Button loading={create.isPending} onClick={() => create.mutate()}>
              Create institution
            </Button>
          </div>
        </section>
      )}

      <div className="mt-6">
        {isLoading && <Skeleton className="h-48 w-full" />}

        {!isLoading && institutions.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-line bg-surface shadow-e1">
            <table className="w-full text-sm">
              <caption className="sr-only">Institutions</caption>
              <thead>
                <tr className="border-b border-line">
                  <Th>Institution</Th>
                  <Th>Prefix</Th>
                  <Th className="hidden sm:table-cell">Users</Th>
                  <Th className="hidden md:table-cell">Added</Th>
                  <Th>Status</Th>
                  <Th><span className="sr-only">Actions</span></Th>
                </tr>
              </thead>
              <tbody>
                {institutions.map((institution) => (
                  <tr key={institution.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3">
                      <p className="font-medium text-ink-900">{institution.name}</p>
                      <p className="font-mono text-caption text-ink-500">{institution.slug}</p>
                    </td>
                    <td className="px-4 py-3 font-mono text-caption text-ink-600">
                      {institution.code}
                    </td>
                    <td className="hidden px-4 py-3 text-ink-600 sm:table-cell">
                      {institution.user_count}
                    </td>
                    <td className="hidden px-4 py-3 text-caption text-ink-500 md:table-cell">
                      {formatDate(institution.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="rounded-full px-2.5 py-0.5 text-caption font-semibold"
                        style={
                          institution.is_active
                            ? {
                                backgroundColor: 'var(--status-resolved-bg)',
                                color: 'var(--status-resolved-fg)',
                              }
                            : {
                                backgroundColor: 'var(--status-declined-bg)',
                                color: 'var(--status-declined-fg)',
                              }
                        }
                      >
                        {institution.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggle.mutate(institution.id)}
                      >
                        {institution.is_active ? 'Suspend' : 'Restore'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!isLoading && institutions.length === 0 && !creating && (
          <div className="rounded-lg border border-dashed border-line bg-surface px-6 py-16 text-center">
            <BuildingLibraryIcon className="mx-auto h-10 w-10 text-ink-500" aria-hidden="true" />
            <h2 className="mt-3 font-display text-lg font-semibold text-ink-900">
              No institutions yet
            </h2>
            <p className="mt-1 text-sm text-ink-600">
              Add the first one to start taking complaints.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4 shadow-e1">
      <p className="text-caption font-bold uppercase tracking-wider text-ink-500">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold text-ink-900">{value ?? 0}</p>
    </div>
  );
}

function Pair({ label, value, mono = false }) {
  return (
    <div className="flex justify-between gap-4">
      <dt>{label}</dt>
      <dd className={`font-semibold ${mono ? 'font-mono' : ''}`}>{value}</dd>
    </div>
  );
}

function Th({ children, className = '' }) {
  return (
    <th
      scope="col"
      className={`px-4 py-3 text-left text-caption font-bold uppercase tracking-wider text-ink-500 ${className}`}
    >
      {children}
    </th>
  );
}
