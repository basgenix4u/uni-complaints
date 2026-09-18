import { useEffect, useState } from 'react';
import { PhotoIcon } from '@heroicons/react/24/outline';

import { attachmentService } from '../../services/api';

/**
 * Thumbnail for an image attachment.
 *
 * The preview endpoint requires a token, so the image is fetched and held
 * as an object URL rather than pointed at directly. The URL is released
 * when the component goes away, otherwise the blob is retained for the
 * lifetime of the page.
 */
export default function AttachmentPreview({ complaintId, attachment, onOpen }) {
  const [source, setSource] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!attachment.has_preview) return undefined;

    let url = null;
    let cancelled = false;

    attachmentService
      .preview(complaintId, attachment.id)
      .then((objectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        url = objectUrl;
        setSource(objectUrl);
      })
      .catch(() => !cancelled && setFailed(true));

    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [complaintId, attachment.id, attachment.has_preview]);

  if (!attachment.has_preview || failed) {
    return (
      <span
        className="flex h-12 w-12 flex-none items-center justify-center rounded-md bg-canvas"
        aria-hidden="true"
      >
        <PhotoIcon className="h-5 w-5 text-ink-500" />
      </span>
    );
  }

  if (!source) {
    return <span className="h-12 w-12 flex-none animate-shimmer rounded-md bg-line/60" aria-hidden="true" />;
  }

  return (
    <button
      type="button"
      onClick={() => onOpen?.(source)}
      className="h-12 w-12 flex-none overflow-hidden rounded-md border border-line focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
      aria-label={`View ${attachment.original_name}`}
    >
      <img
        src={source}
        alt={attachment.original_name}
        className="h-full w-full object-cover"
        loading="lazy"
      />
    </button>
  );
}
