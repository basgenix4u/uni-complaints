import { cn } from '../../utils/cn';

/**
 * Loading placeholder.
 *
 * Preferred over a spinner for content areas: a skeleton communicates the
 * shape of what is arriving, which makes the wait feel shorter on the slow
 * and variable connections many users are on.
 */
export default function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn(
        'animate-shimmer rounded-md bg-line/60',
        'bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,.45)_50%,transparent_100%)]',
        'bg-[length:200%_100%]',
        className,
      )}
      aria-hidden="true"
      {...props}
    />
  );
}

export function SkeletonList({ rows = 5 }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="rounded-lg border border-line bg-surface p-4">
          <div className="flex items-center justify-between gap-4">
            <Skeleton className="h-4 w-2/5" />
            <Skeleton className="h-6 w-24 rounded-full" />
          </div>
          <Skeleton className="mt-3 h-3 w-4/5" />
          <Skeleton className="mt-2 h-3 w-1/3" />
        </div>
      ))}
    </div>
  );
}
