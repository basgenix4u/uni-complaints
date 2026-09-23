import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRightIcon,
  ExclamationTriangleIcon,
  LockClosedIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/Field';
import Skeleton from '../../components/ui/Skeleton';
import { ALL_CATEGORIES, categoryLabel } from '../../utils/status';
import { errorMessage, routingService } from '../../services/api';

const PRIORITY_LABELS = {
  urgent: 'Urgent',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

/**
 * Who answers what.
 *
 * Routing is the institution's own policy, so it is edited here rather
 * than shipped in the code. Every university disagrees with part of the
 * default table and the disagreements are not mistakes: scholarships sit
 * with Bursary at one and with Student Affairs at another.
 */
export default function RoutingRules() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(null);
  const [policyEditing, setPolicyEditing] = useState(null);
  const [notice, setNotice] = useState('');
  const [problem, setProblem] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['routing-rules'],
    queryFn: () => routingService.rules(),
  });

  const { data: policyData, isLoading: policiesLoading } = useQuery({
    queryKey: ['priority-policies'],
    queryFn: () => routingService.priorityPolicies(),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['routing-rules'] });
    queryClient.invalidateQueries({ queryKey: ['priority-policies'] });
  };

  const announce = (message) => {
    setNotice(message);
    setProblem('');
    setTimeout(() => setNotice(''), 4000);
  };

  const save = useMutation({
    mutationFn: (payload) => routingService.saveRule(payload),
    onSuccess: () => {
      setEditing(null);
      announce('Routing updated.');
      refresh();
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const savePolicy = useMutation({
    mutationFn: ({ priority, ...payload }) =>
      routingService.savePriorityPolicy(priority, payload),
    onSuccess: () => {
      setPolicyEditing(null);
      announce('Priority policy updated. New complaints will use it.');
      refresh();
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const seed = useMutation({
    mutationFn: () => routingService.seed(),
    onSuccess: (result) => {
      announce(
        result.rules_created || result.units_created || result.priority_policies_created
          ? `Added ${result.units_created} unit(s), ${result.rules_created} rule(s) and ${result.priority_policies_created} priority policy row(s).`
          : 'Everything was already in place.',
      );
      refresh();
    },
    onError: (error) => setProblem(errorMessage(error)),
  });

  const units = data?.units ?? [];
  const rules = data?.rules ?? [];
  const policies = policyData?.policies ?? [];
  const byCategory = Object.fromEntries(rules.map((rule) => [rule.category, rule]));
  const unrouted = ALL_CATEGORIES.filter((item) => !byCategory[item.value]);

  if (isLoading || policiesLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-8">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900">
            Who answers what
          </h1>
          <p className="mt-1 max-w-xl text-ink-600">
            A student should not have to work out which office owns their problem. These rules
            decide that for them, the moment a complaint is filed.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => seed.mutate()}
          loading={seed.isPending}
          className="shrink-0"
        >
          <SparklesIcon className="h-5 w-5" aria-hidden="true" />
          Fill in the usual
        </Button>
      </div>

      <div aria-live="polite" className="mt-4 empty:mt-0">
        {notice && (
          <p className="rounded-md bg-brand-50 px-4 py-2.5 text-sm font-medium text-brand-800">
            {notice}
          </p>
        )}
        {problem && (
          <p role="alert" className="rounded-md bg-[#FEF2F2] px-4 py-2.5 text-sm font-medium text-[#B91C1C]">
            {problem}
          </p>
        )}
      </div>

      <section className="mt-6 rounded-lg border border-line bg-surface p-5 shadow-e1">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink-900">
            What each priority means
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-600">
            These are working hours, not clock hours. They decide when a complaint must be
            acknowledged, how its category deadline is shortened or extended, and how long each
            rung of the escalation ladder gets before the next person is told.
          </p>
        </div>

        {policies.length === 0 ? (
          <p className="mt-4 rounded-md bg-canvas px-4 py-3 text-sm text-ink-600">
            No priority policy is recorded yet. Use “Fill in the usual” to add a reviewable
            starting point; legacy deadlines remain in force until then.
          </p>
        ) : (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {policies.map((policy) => {
              const isEditing = policyEditing?.priority === policy.priority;
              return (
                <div key={policy.priority} className="rounded-md border border-line p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold text-ink-900">
                        {PRIORITY_LABELS[policy.priority] || policy.priority}
                      </h3>
                      <p className="mt-1 text-caption leading-relaxed text-ink-500">
                        Acknowledge in {policy.acknowledge_hours}h · resolve at{' '}
                        {policy.resolution_factor}× category SLA · next rung in{' '}
                        {policy.escalation_step_hours}h · remind {policy.reminder_hours_before_due}h
                        before due
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setPolicyEditing(isEditing ? null : { ...policy })}
                    >
                      {isEditing ? 'Cancel' : 'Change'}
                    </Button>
                  </div>

                  {isEditing && (
                    <form
                      className="mt-4 grid grid-cols-2 gap-3 border-t border-line pt-4"
                      onSubmit={(event) => {
                        event.preventDefault();
                        savePolicy.mutate({
                          ...policyEditing,
                          acknowledge_hours: Number(policyEditing.acknowledge_hours),
                          resolution_factor: Number(policyEditing.resolution_factor),
                          escalation_step_hours: Number(policyEditing.escalation_step_hours),
                          reminder_hours_before_due: Number(
                            policyEditing.reminder_hours_before_due,
                          ),
                        });
                      }}
                    >
                      <Input
                        label="Hours to acknowledge"
                        type="number"
                        min="1"
                        value={policyEditing.acknowledge_hours}
                        onChange={(event) =>
                          setPolicyEditing({
                            ...policyEditing,
                            acknowledge_hours: event.target.value,
                          })
                        }
                      />
                      <Input
                        label="Resolution multiplier"
                        type="number"
                        min="0.05"
                        max="10"
                        step="0.05"
                        value={policyEditing.resolution_factor}
                        onChange={(event) =>
                          setPolicyEditing({
                            ...policyEditing,
                            resolution_factor: event.target.value,
                          })
                        }
                      />
                      <Input
                        label="Hours before next rung"
                        type="number"
                        min="1"
                        value={policyEditing.escalation_step_hours}
                        onChange={(event) =>
                          setPolicyEditing({
                            ...policyEditing,
                            escalation_step_hours: event.target.value,
                          })
                        }
                      />
                      <Input
                        label="Reminder hours before due"
                        type="number"
                        min="0"
                        value={policyEditing.reminder_hours_before_due}
                        onChange={(event) =>
                          setPolicyEditing({
                            ...policyEditing,
                            reminder_hours_before_due: event.target.value,
                          })
                        }
                      />
                      <div className="col-span-2">
                        <Button type="submit" size="sm" loading={savePolicy.isPending}>
                          Save {policy.priority}
                        </Button>
                      </div>
                    </form>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {units.length === 0 && (
        <p className="mt-6 flex items-start gap-2 rounded-md border border-line bg-surface p-4 text-sm text-ink-600">
          <ExclamationTriangleIcon className="h-5 w-5 shrink-0 text-ink-500" aria-hidden="true" />
          There are no units yet. Add them under Departments, or use “Fill in the usual” to start
          from the ones most Nigerian universities have.
        </p>
      )}

      {unrouted.length > 0 && units.length > 0 && (
        <p className="mt-6 rounded-md border border-line bg-surface p-4 text-sm text-ink-600">
          {unrouted.length} categor{unrouted.length === 1 ? 'y has' : 'ies have'} no rule.
          Complaints in {unrouted.length === 1 ? 'it' : 'them'} still arrive, but nobody is assigned
          to answer.
        </p>
      )}

      <ul className="mt-6 space-y-2">
        {ALL_CATEGORIES.map((item) => {
          const rule = byCategory[item.value];
          const isEditing = editing?.category === item.value;

          return (
            <li key={item.value} className="rounded-lg border border-line bg-surface">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 p-4">
                <span className="font-medium text-ink-900">{item.label}</span>
                <ArrowRightIcon className="h-4 w-4 text-ink-500" aria-hidden="true" />
                <span className={rule ? 'text-ink-700' : 'text-ink-500 italic'}>
                  {!rule && 'nobody yet'}
                  {rule?.target_type === 'department' && "the student's own department"}
                  {rule?.target_type === 'unit' && (rule.department || 'nobody yet')}
                </span>
                {rule?.is_confidential && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-caption font-semibold text-brand-800">
                    <LockClosedIcon className="h-3.5 w-3.5" aria-hidden="true" />
                    Confidential
                  </span>
                )}
                {rule?.sla_hours && (
                  <span className="text-caption text-ink-500">{rule.sla_hours}h to resolve</span>
                )}
                <Button
                  size="sm"
                  variant="ghost"
                  className="ml-auto"
                  onClick={() =>
                    setEditing(
                      isEditing
                        ? null
                        : {
                            category: item.value,
                            target_type: rule?.target_type ?? 'unit',
                            department_id: rule?.department_id ?? '',
                            sla_hours: rule?.sla_hours ?? '',
                            is_confidential: rule?.is_confidential ?? false,
                          },
                    )
                  }
                >
                  {isEditing ? 'Cancel' : rule ? 'Change' : 'Set up'}
                </Button>
              </div>

              {isEditing && (
                <form
                  className="grid gap-4 border-t border-line p-4 sm:grid-cols-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    save.mutate({
                      category: editing.category,
                      target_type: editing.target_type,
                      department_id:
                        editing.target_type === 'unit' ? editing.department_id || null : null,
                      sla_hours: editing.sla_hours === '' ? null : Number(editing.sla_hours),
                      is_confidential: editing.is_confidential,
                    });
                  }}
                >
                  <Select
                    label="Send it to"
                    value={editing.target_type}
                    onChange={(event) =>
                      setEditing({ ...editing, target_type: event.target.value })
                    }
                  >
                    <option value="unit">A named unit</option>
                    <option value="department">The student&apos;s own department</option>
                  </Select>

                  {editing.target_type === 'unit' ? (
                    <Select
                      label="Which unit"
                      value={editing.department_id}
                      onChange={(event) =>
                        setEditing({ ...editing, department_id: event.target.value })
                      }
                    >
                      <option value="">Choose a unit</option>
                      {units.map((unit) => (
                        <option key={unit.id} value={unit.id}>
                          {unit.name}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <p className="self-end text-caption text-ink-500">
                      A disputed grade belongs with the department that set it, so the destination
                      depends on who is complaining.
                    </p>
                  )}

                  <Input
                    label="Hours to resolve"
                    type="number"
                    min="1"
                    value={editing.sla_hours}
                    hint="Leave blank to use the institution default."
                    onChange={(event) => setEditing({ ...editing, sla_hours: event.target.value })}
                  />

                  <label className="flex items-start gap-2.5 self-end text-sm text-ink-700">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 rounded border-line text-brand-700 focus:outline-2 focus:outline-offset-2 focus:outline-brand-700"
                      checked={editing.is_confidential}
                      onChange={(event) =>
                        setEditing({ ...editing, is_confidential: event.target.checked })
                      }
                    />
                    <span>
                      Keep out of the general queue
                      <span className="block text-caption text-ink-500">
                        Only the handling unit and administrators can read it. Use this for
                        anything naming a member of staff.
                      </span>
                    </span>
                  </label>

                  <div className="sm:col-span-2">
                    <Button type="submit" size="sm" loading={save.isPending}>
                      Save {categoryLabel(editing.category).toLowerCase()}
                    </Button>
                  </div>
                </form>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
