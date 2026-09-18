import { useRef, useState } from 'react';
import {
  ArrowDownTrayIcon,
  DocumentIcon,
  LockClosedIcon,
  PaperClipIcon,
  PhotoIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

import Button from '../ui/Button';
import { attachmentService, errorMessage } from '../../services/api';

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPT = 'image/jpeg,image/png,image/webp,image/heic,application/pdf,.doc,.docx';

function readableSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function AttachmentList({
  complaintId,
  attachments = [],
  canUpload = true,
  canMarkInternal = false,
  onChange,
}) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const upload = async (file, isInternal = false) => {
    if (!file) return;

    // Checked here as well as on the server so the user is told before
    // spending data on the upload.
    if (file.size > MAX_BYTES) {
      setError(`That file is ${readableSize(file.size)}. The limit is 5 MB.`);
      return;
    }

    setBusy(true);
    setError('');
    try {
      await attachmentService.upload(complaintId, file, isInternal);
      onChange?.();
    } catch (uploadError) {
      setError(errorMessage(uploadError, 'We could not attach that file.'));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const download = async (file) => {
    setError('');
    try {
      await attachmentService.download(complaintId, file.id, file.original_name);
    } catch (downloadError) {
      setError(errorMessage(downloadError, 'We could not download that file.'));
    }
  };

  const remove = async (attachmentId) => {
    setBusy(true);
    try {
      await attachmentService.remove(complaintId, attachmentId);
      onChange?.();
    } catch (removeError) {
      setError(errorMessage(removeError, 'We could not remove that file.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-bold text-ink-900">
        Attachments {attachments.length > 0 && `(${attachments.length})`}
      </h3>

      {attachments.length === 0 && (
        <p className="text-sm text-ink-500">Nothing attached yet.</p>
      )}

      <ul className="space-y-2">
        {attachments.map((file) => {
          const Icon = file.is_image ? PhotoIcon : DocumentIcon;
          return (
            <li
              key={file.id}
              className="flex items-center gap-3 rounded-md border border-line bg-surface px-3.5 py-2.5"
            >
              <Icon className="h-5 w-5 flex-none text-ink-500" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink-900">{file.original_name}</p>
                <p className="text-caption text-ink-500">
                  {readableSize(file.size_bytes)}
                  {file.uploaded_by && ` · ${file.uploaded_by}`}
                </p>
              </div>

              {file.is_internal && (
                <span
                  className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-caption font-semibold"
                  style={{ backgroundColor: 'var(--status-progress-bg)', color: 'var(--status-progress-fg)' }}
                >
                  <LockClosedIcon className="h-3 w-3" aria-hidden="true" />
                  Private
                </span>
              )}

              <button
                type="button"
                onClick={() => download(file)}
                disabled={busy}
                className="inline-flex h-11 w-11 items-center justify-center rounded-md text-ink-500 hover:bg-brand-50 hover:text-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700 disabled:opacity-50"
                aria-label={`Download ${file.original_name}`}
              >
                <ArrowDownTrayIcon className="h-5 w-5" aria-hidden="true" />
              </button>

              {onChange && (
                <button
                  type="button"
                  onClick={() => remove(file.id)}
                  disabled={busy}
                  className="inline-flex h-11 w-11 items-center justify-center rounded-md text-ink-500 hover:bg-[#FEF2F2] hover:text-[#B91C1C] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700 disabled:opacity-50"
                  aria-label={`Remove ${file.original_name}`}
                >
                  <TrashIcon className="h-5 w-5" aria-hidden="true" />
                </button>
              )}
            </li>
          );
        })}
      </ul>

      {error && (
        <p role="alert" aria-live="polite" className="text-caption font-medium text-[#B91C1C]">
          {error}
        </p>
      )}

      {canUpload && attachments.length < 5 && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            id={`upload-${complaintId}`}
            onChange={(event) => upload(event.target.files?.[0])}
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            loading={busy}
            onClick={() => inputRef.current?.click()}
          >
            <PaperClipIcon className="h-4 w-4" aria-hidden="true" />
            Attach a file
          </Button>

          {canMarkInternal && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={busy}
              onClick={() => {
                const picker = document.createElement('input');
                picker.type = 'file';
                picker.accept = ACCEPT;
                picker.onchange = (event) => upload(event.target.files?.[0], true);
                picker.click();
              }}
            >
              <LockClosedIcon className="h-4 w-4" aria-hidden="true" />
              Attach privately
            </Button>
          )}

          <span className="text-caption text-ink-500">
            Images, PDF or Word. Up to 5 MB each.
          </span>
        </div>
      )}
    </section>
  );
}
