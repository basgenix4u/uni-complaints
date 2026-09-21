import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AcademicCapIcon,
  ArrowUpTrayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';

import Button from '../../components/ui/Button';
import { Input, Select, Textarea } from '../../components/ui/Field';
import Skeleton from '../../components/ui/Skeleton';
import { academicService, errorMessage } from '../../services/api';

/**
 * The academic tree and the student register.
 *
 * This is the screen that makes `verification_mode="register"` real.
 * Without it the tables existed, the import logic existed, and neither
 * could be reached — so every institution silently fell back to an
 * administrator approving every single registration by hand.
 *
 * The register import is the highest-consequence action an administrator
 * can take here: it decides who is allowed to sign up. It is therefore
 * always previewed before it is applied, and the preview is not
 * skippable.
 */
export default function AcademicStructure() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('structure');
  const [notice, setNotice] = useState('');
  const [problem, setProblem] = useState('');

  const announce = (message) => {
    setNotice(message);
    setProblem('');
    setTimeout(() => setNotice(''), 4000);
  };
  const complain = (error) => setProblem(errorMessage(error));

  const { data: sessionData, isLoading: loadingSessions } = useQuery({
    queryKey: ['academic-sessions'],
    queryFn: () => academicService.sessions(),
  });

  const { data: facultyData, isLoading: loadingFaculties } = useQuery({
    queryKey: ['academic-faculties'],
    queryFn: () => academicService.faculties(),
  });

  const { data: registerData } = useQuery({
    queryKey: ['register-summary'],
    queryFn: () => academicService.registerSummary(),
  });

  const refresh = (...keys) =>
    keys.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));

  const sessions = sessionData?.sessions ?? [];
  const faculties = facultyData?.faculties ?? [];
  const summary = registerData?.summary;

  const TABS = [
    { key: 'structure', label: 'Faculties' },
    { key: 'register', label: 'Student register' },
    { key: 'sessions', label: 'Sessions' },
  ];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900">
        Academic structure
      </h1>
      <p className="mt-1 max-w-xl text-ink-600">
        Where your students actually sit, and the register used to confirm they are yours. This is
        separate from the units that resolve complaints.
      </p>

      {summary?.advice && (
        <p className="mt-4 flex items-start gap-2.5 rounded-md border border-[#FCD34D] bg-[#FFFBEB] p-4 text-sm text-[#78350F]">
          <ExclamationTriangleIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
          <span>{summary.advice}</span>
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

      <div className="mt-6 flex gap-1 rounded-lg border border-line bg-surface p-1" role="tablist">
        {TABS.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            aria-selected={tab === entry.key}
            onClick={() => setTab(entry.key)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-semibold transition-colors ${
              tab === entry.key ? 'bg-brand-700 text-white' : 'text-ink-600 hover:bg-brand-50'
            }`}
          >
            {entry.label}
          </button>
        ))}
      </div>

      {tab === 'structure' && (
        <Structure
          faculties={faculties}
          isLoading={loadingFaculties}
          onDone={(message) => {
            announce(message);
            refresh('academic-faculties');
          }}
          onError={complain}
        />
      )}

      {tab === 'register' && (
        <Register
          sessions={sessions}
          summary={summary}
          onDone={(message) => {
            announce(message);
            refresh('register-summary');
          }}
          onError={complain}
        />
      )}

      {tab === 'sessions' && (
        <Sessions
          sessions={sessions}
          isLoading={loadingSessions}
          onDone={(message) => {
            announce(message);
            refresh('academic-sessions', 'register-summary');
          }}
          onError={complain}
        />
      )}
    </div>
  );
}

function Structure({ faculties, isLoading, onDone, onError }) {
  const [name, setName] = useState('');
  const [bulk, setBulk] = useState('');
  const [preview, setPreview] = useState(null);
  const [adding, setAdding] = useState(null);
  const [departmentName, setDepartmentName] = useState('');

  const createFaculty = useMutation({
    mutationFn: (payload) => academicService.createFaculty(payload),
    onSuccess: () => {
      setName('');
      onDone('Faculty added.');
    },
    onError,
  });

  const createDepartment = useMutation({
    mutationFn: ({ facultyId, payload }) => academicService.createDepartment(facultyId, payload),
    onSuccess: () => {
      setDepartmentName('');
      setAdding(null);
      onDone('Department added.');
    },
    onError,
  });

  const importTree = useMutation({
    mutationFn: ({ csv, dry_run }) => academicService.importStructure({ csv, dry_run }),
    onSuccess: (result, variables) => {
      if (variables.dry_run) {
        setPreview(result.summary);
        return;
      }
      setPreview(null);
      setBulk('');
      onDone(
        `Added ${result.summary.faculties_created} facult${
          result.summary.faculties_created === 1 ? 'y' : 'ies'
        } and ${result.summary.departments_created} department(s).`,
      );
    },
    onError,
  });

  if (isLoading) return <Skeleton className="mt-4 h-64 w-full" />;

  return (
    <div className="mt-4 space-y-6">
      <form
        className="flex flex-wrap items-end gap-3 rounded-lg border border-line bg-surface p-5"
        onSubmit={(event) => {
          event.preventDefault();
          createFaculty.mutate({ name });
        }}
      >
        <div className="min-w-[14rem] flex-1">
          <Input
            label="Add a faculty"
            placeholder="Faculty of Engineering"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </div>
        <Button type="submit" loading={createFaculty.isPending}>
          <PlusIcon className="h-5 w-5" aria-hidden="true" />
          Add
        </Button>
      </form>

      <details className="rounded-lg border border-line bg-surface p-5">
        <summary className="cursor-pointer font-semibold text-ink-900">
          Or paste the whole tree at once
        </summary>
        <div className="mt-4 space-y-3">
          <Textarea
            label="Faculties and departments"
            rows={6}
            placeholder={'faculty,department\nEngineering,Computer Engineering\nScience,Microbiology'}
            hint="One per line, with a header row. Faculties are created as they appear."
            value={bulk}
            onChange={(event) => {
              setBulk(event.target.value);
              setPreview(null);
            }}
          />

          {preview && (
            <div className="rounded-md border border-line bg-canvas p-4 text-sm">
              <p className="font-semibold text-ink-900">
                {preview.faculties_created} new facult
                {preview.faculties_created === 1 ? 'y' : 'ies'},{' '}
                {preview.departments_created} new department(s), {preview.skipped} already there.
              </p>
              {(preview.problems ?? []).slice(0, 6).map((line) => (
                <p key={line} className="mt-1 text-caption text-[#B45309]">
                  {line}
                </p>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={!bulk.trim()}
              loading={importTree.isPending && !preview}
              onClick={() => importTree.mutate({ csv: bulk, dry_run: true })}
            >
              Check it first
            </Button>
            <Button
              disabled={!preview}
              loading={importTree.isPending && Boolean(preview)}
              onClick={() => importTree.mutate({ csv: bulk, dry_run: false })}
            >
              Apply
            </Button>
          </div>
        </div>
      </details>

      {faculties.length === 0 ? (
        <div className="flex items-start gap-3 rounded-lg border border-line bg-surface p-6">
          <AcademicCapIcon className="h-6 w-6 shrink-0 text-ink-500" aria-hidden="true" />
          <div>
            <p className="font-medium text-ink-900">No faculties yet.</p>
            <p className="mt-1 text-sm text-ink-600">
              Academic complaints route to a student&apos;s own department, so this has to exist
              before that can work.
            </p>
          </div>
        </div>
      ) : (
        <ul className="space-y-2">
          {faculties.map((faculty) => (
            <li key={faculty.id} className="rounded-lg border border-line bg-surface p-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-medium text-ink-900">{faculty.name}</span>
                <span className="text-caption text-ink-500">
                  {(faculty.departments ?? []).length} department(s)
                  {faculty.dean ? ` · dean ${faculty.dean}` : ''}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  className="ml-auto"
                  onClick={() => setAdding(adding === faculty.id ? null : faculty.id)}
                >
                  {adding === faculty.id ? 'Cancel' : 'Add department'}
                </Button>
              </div>

              {(faculty.departments ?? []).length > 0 && (
                <p className="mt-2 text-sm text-ink-600">
                  {faculty.departments.map((d) => d.name).join(' · ')}
                </p>
              )}

              {adding === faculty.id && (
                <form
                  className="mt-3 flex flex-wrap items-end gap-3 border-t border-line pt-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    createDepartment.mutate({
                      facultyId: faculty.id,
                      payload: { name: departmentName },
                    });
                  }}
                >
                  <div className="min-w-[14rem] flex-1">
                    <Input
                      label="Department name"
                      placeholder="Computer Engineering"
                      value={departmentName}
                      onChange={(event) => setDepartmentName(event.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" size="sm" loading={createDepartment.isPending}>
                    Add
                  </Button>
                </form>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Register({ sessions, summary, onDone, onError }) {
  const fileInput = useRef(null);
  const [file, setFile] = useState(null);
  const [sessionId, setSessionId] = useState('');
  const [preview, setPreview] = useState(null);

  const runImport = useMutation({
    mutationFn: ({ dry_run }) => academicService.importRegister({ file, sessionId, dry_run }),
    onSuccess: (result, variables) => {
      if (variables.dry_run) {
        setPreview(result.summary);
        return;
      }
      setPreview(null);
      setFile(null);
      if (fileInput.current) fileInput.current.value = '';
      onDone(
        `${result.summary.created} added, ${result.summary.updated} updated, ${result.summary.skipped} unchanged.`,
      );
    },
    onError,
  });

  const current = sessions.find((s) => s.is_current);

  return (
    <div className="mt-4 space-y-5">
      <div className="grid gap-4 rounded-lg border border-line bg-surface p-5 sm:grid-cols-3">
        <Stat label="In the register" value={summary?.total ?? 0} />
        <Stat label="Claimed by a student" value={summary?.claimed ?? 0} />
        <Stat label="Current session" value={summary?.current_session?.name ?? 'None open'} />
      </div>

      <div className="space-y-4 rounded-lg border border-line bg-surface p-5">
        <div>
          <label
            htmlFor="register-file"
            className="block text-sm font-semibold text-ink-700"
          >
            The register, as a CSV
          </label>
          <input
            id="register-file"
            ref={fileInput}
            type="file"
            accept=".csv,text/csv"
            className="mt-1.5 block w-full rounded-md border border-line bg-surface px-3.5 py-2.5 text-sm text-ink-900 file:mr-3 file:rounded file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-brand-800"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setPreview(null);
            }}
          />
          <p className="mt-1.5 text-caption text-ink-500">
            Needs <code>matric_number</code> and <code>full_name</code>. Optionally faculty,
            department, programme, level and status.
          </p>
        </div>

        {sessions.length > 1 && (
          <Select
            label="Import into"
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
          >
            <option value="">
              {current ? `${current.name} (current)` : 'Choose a session'}
            </option>
            {sessions.map((session) => (
              <option key={session.id} value={session.id}>
                {session.name}
              </option>
            ))}
          </Select>
        )}

        {preview && (
          <div className="rounded-md border border-line bg-canvas p-4 text-sm">
            <p className="font-semibold text-ink-900">
              {preview.rows_read} row(s) read into {preview.session}: {preview.created} new,{' '}
              {preview.updated} updated, {preview.skipped} unchanged.
            </p>
            <p className="mt-1 text-caption text-ink-600">
              Nothing has been written yet. Students already registered keep their accounts.
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
            disabled={!file}
            loading={runImport.isPending && !preview}
            onClick={() => runImport.mutate({ dry_run: true })}
          >
            <ArrowUpTrayIcon className="h-5 w-5" aria-hidden="true" />
            Check the file
          </Button>
          {/* Applying is deliberately gated behind the preview: this decides
              who may sign up, and it is not an action to take blind. */}
          <Button
            disabled={!preview || preview.rows_read === 0}
            loading={runImport.isPending && Boolean(preview)}
            onClick={() => runImport.mutate({ dry_run: false })}
          >
            Import {preview?.rows_read ? `${preview.rows_read} ` : ''}students
          </Button>
        </div>
      </div>
    </div>
  );
}

function Sessions({ sessions, isLoading, onDone, onError }) {
  const [name, setName] = useState('');

  const create = useMutation({
    mutationFn: (payload) => academicService.createSession(payload),
    onSuccess: () => {
      setName('');
      onDone('Session opened.');
    },
    onError,
  });

  const makeCurrent = useMutation({
    mutationFn: (id) => academicService.setCurrentSession(id),
    onSuccess: () => onDone('Current session changed.'),
    onError,
  });

  if (isLoading) return <Skeleton className="mt-4 h-48 w-full" />;

  return (
    <div className="mt-4 space-y-5">
      <form
        className="flex flex-wrap items-end gap-3 rounded-lg border border-line bg-surface p-5"
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate({ name, is_current: true });
        }}
      >
        <div className="min-w-[12rem] flex-1">
          <Input
            label="Open a session"
            placeholder="2025/2026"
            hint="Written the way your institution writes it."
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </div>
        <Button type="submit" loading={create.isPending}>
          Open
        </Button>
      </form>

      {sessions.length === 0 ? (
        <p className="rounded-lg border border-line bg-surface p-5 text-sm text-ink-600">
          No sessions yet. A register is imported into a session, so open the current one first.
        </p>
      ) : (
        <ul className="space-y-2">
          {sessions.map((session) => (
            <li
              key={session.id}
              className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface p-4"
            >
              <span className="font-medium text-ink-900">{session.name}</span>
              {session.is_current ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-0.5 text-caption font-semibold text-brand-800">
                  <CheckCircleIcon className="h-3.5 w-3.5" aria-hidden="true" />
                  Current
                </span>
              ) : (
                <Button
                  size="sm"
                  variant="ghost"
                  className="ml-auto"
                  loading={makeCurrent.isPending}
                  onClick={() => makeCurrent.mutate(session.id)}
                >
                  Make current
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-caption font-bold uppercase tracking-wider text-ink-500">{label}</p>
      <p className="mt-0.5 font-display text-xl font-semibold text-ink-900">{value}</p>
    </div>
  );
}
