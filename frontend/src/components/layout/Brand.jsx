/**
 * The Resolve mark.
 *
 * An inline SVG rather than a file: it is the first thing on every
 * signed-out page, and at this size the markup costs less than the
 * request would. It also inherits currentColor, so the same component
 * works on the dark panel and the light form.
 */
export default function Brand({ className = 'h-12 w-12', title }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      role={title ? 'img' : 'presentation'}
      aria-label={title}
      aria-hidden={title ? undefined : 'true'}
    >
      <circle cx="24" cy="24" r="24" className="fill-white" />
      <circle cx="24" cy="24" r="21.5" className="fill-brand-800" />
      {/* A 'U' drawn as a stroke so it stays crisp at any size. */}
      <path
        d="M17 15.5v10.8a7 7 0 0 0 14 0V15.5"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="3.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
