import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircleIcon, UserPlusIcon } from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import Skeleton from '../../components/ui/Skeleton';
import { adminService, errorMessage } from '../../services/api';

/**
 * Students waiting to be confirmed as students.
 *
 * Each row is somebody locked out until a person looks, so the reason
 * the automatic check did not settle it is shown here rather than making
 * the administrator go and find it.
 */
export default function PendingRegistrations() {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState('');
  const [problem, setProblem] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['pending-registrations'],
    queryFn: () => adminService.registrations(),
  });

  const decide = useMutation({
    mutationFn: ({ id, decision }) => adminService.decideRegistration(id, decision),
    onSuccess: (_result, variables) => {
      setProblem('');
      setNotice(variables.decision === 'approved' ? 'Approved.' : 'Rejected.');
      setTimeout(() => setNotice(''), 3000);
      queryClient.invalidateQueries({ queryKey: ['pending-registrations'] });
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const rows = data?.registrations ?? [];

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-8">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900">
        Registrations to check
      </h1>
      <p className="mt-1 max-w-xl text-ink-600">
        These people say they study here, and the student register could not confirm it on its
        own. Each is locked out until you decide.
      </p>

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

      {rows.length === 0 ? (
        <div className="mt-6 flex items-start gap-3 rounded-lg border border-line bg-surface p-6">
          <CheckCircleIcon className="h-6 w-6 shrink-0 text-brand-700" aria-hidden="true" />
          <div>
            <p className="font-medium text-ink-900">Nothing waiting.</p>
            <p className="mt-1 text-sm text-ink-600">
              Every registration has been matched against the register or already decided.
            </p>
          </div>
        </div>
      ) : (
        <ul className="mt-6 space-y-3">
          {rows.map((person) => (
            <li key={person.id} className="rounded-lg border border-line bg-surface p-4">
              <div className="flex flex-wrap items-start gap-3">
                <UserPlusIcon className="mt-0.5 h-5 w-5 shrink-0 text-ink-500" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-ink-900">{person.full_name}</p>
                  <p className="text-caption text-ink-500">
                    {person.email}
                    {person.matric_number ? ` · ${person.matric_number}` : ''}
                  </p>
                  <p className="mt-1.5 text-sm text-ink-700">{person.reason}</p>

                  {person.register_match && (
                    <p className="mt-1 text-caption text-ink-500">
                      Register says: {person.register_match.full_name}
                      {person.register_match.department
                        ? ` · ${person.register_match.department}`
                        : ''}
                      {person.register_match.level ? ` · level ${person.register_match.level}` : ''}
                    </p>
                  )}

                  {!person.is_verified && (
                    <p className="mt-1 text-caption font-medium text-[#B45309]">
                      They have not confirmed their email address yet.
                    </p>
                  )}
                </div>

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    loading={decide.isPending}
                    onClick={() => decide.mutate({ id: person.id, decision: 'approved' })}
                  >
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => decide.mutate({ id: person.id, decision: 'rejected' })}
                  >
                    Reject
                  </Button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
