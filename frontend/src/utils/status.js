import {
  ArchiveBoxIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  HandRaisedIcon,
  InboxArrowDownIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

/**
 * Status presentation.
 *
 * Several of these hues are indistinguishable under deuteranopia: amber and
 * red measure 1.19 contrast once simulated, and blue and slate 1.20. Status
 * therefore always carries an icon and a label, never colour alone.
 */
export const STATUS = {
  submitted: {
    label: 'Submitted',
    icon: InboxArrowDownIcon,
    fg: 'var(--status-submitted-fg)',
    bg: 'var(--status-submitted-bg)',
    hint: 'Waiting to be acknowledged',
  },
  acknowledged: {
    label: 'Acknowledged',
    icon: EyeIcon,
    fg: 'var(--status-acknowledged-fg)',
    bg: 'var(--status-acknowledged-bg)',
    hint: 'Seen, and being looked into',
  },
  in_progress: {
    label: 'In progress',
    icon: ArrowPathIcon,
    fg: 'var(--status-progress-fg)',
    bg: 'var(--status-progress-bg)',
    hint: 'Someone is working on it',
  },
  awaiting_student: {
    label: 'Awaiting you',
    icon: HandRaisedIcon,
    fg: 'var(--status-acknowledged-fg)',
    bg: 'var(--status-acknowledged-bg)',
    hint: 'They need something from you',
  },
  resolved: {
    label: 'Resolved',
    icon: CheckCircleIcon,
    fg: 'var(--status-resolved-fg)',
    bg: 'var(--status-resolved-bg)',
    hint: 'Sorted',
  },
  closed: {
    label: 'Closed',
    icon: ArchiveBoxIcon,
    fg: 'var(--status-closed-fg)',
    bg: 'var(--status-closed-bg)',
    hint: 'Finished and filed',
  },
  declined: {
    label: 'Not accepted',
    icon: XCircleIcon,
    fg: 'var(--status-declined-fg)',
    bg: 'var(--status-declined-bg)',
    hint: 'A reason was given',
  },
  overdue: {
    label: 'Overdue',
    icon: ExclamationTriangleIcon,
    fg: 'var(--status-overdue-fg)',
    bg: 'var(--status-overdue-bg)',
    hint: 'Past the response deadline',
  },
};

export const PRIORITY = {
  low: { label: 'Low', hint: 'Not urgent' },
  medium: { label: 'Medium', hint: 'Should be looked at soon' },
  high: { label: 'High', hint: 'Needs prompt attention' },
  urgent: { label: 'Urgent', hint: 'Critical' },
};

export const getStatus = (key) => STATUS[key] || STATUS.submitted;

/** Order shown on the progress rail. Declined leaves the happy path. */
export const RAIL = ['submitted', 'acknowledged', 'in_progress', 'resolved', 'closed'];

/**
 * The 19 categories are grouped into 6.
 *
 * A flat list of 19 is a decision wall; grouping keeps the choice within
 * the span most people hold comfortably in mind.
 */
export const CATEGORY_GROUPS = [
  {
    name: 'Academics',
    icon: '📘',
    items: [
      { value: 'result_issues', label: 'Results' },
      { value: 'examination', label: 'Examinations' },
      { value: 'course_registration', label: 'Course registration' },
      { value: 'academic_advising', label: 'Academic advising' },
      { value: 'department_issue', label: 'Department administration' },
      { value: 'faculty_issue', label: 'Faculty administration' },
    ],
  },
  {
    name: 'Records and documents',
    icon: '📄',
    items: [
      { value: 'transcript', label: 'Transcripts' },
      { value: 'certificate', label: 'Certificates' },
      { value: 'id_card', label: 'ID card' },
      { value: 'clearance', label: 'Clearance' },
    ],
  },
  {
    name: 'Money',
    icon: '💳',
    items: [
      { value: 'fees_payment', label: 'Fees and payment' },
      { value: 'scholarship', label: 'Scholarship' },
    ],
  },
  {
    name: 'Campus life',
    icon: '🏠',
    items: [
      { value: 'accommodation', label: 'Accommodation' },
      { value: 'student_welfare', label: 'Student welfare' },
      { value: 'sug_support', label: 'Students’ Union support' },
      { value: 'ict_portal', label: 'Portal, email and ICT' },
      { value: 'facilities', label: 'Facilities and maintenance' },
      { value: 'library', label: 'Library' },
      { value: 'medical', label: 'Medical and health' },
    ],
  },
  {
    name: 'Admissions',
    icon: '🎒',
    items: [
      { value: 'admission', label: 'Admission' },
      { value: 'registration', label: 'Registration' },
      { value: 'transfer', label: 'Transfer' },
    ],
  },
  {
    name: 'Conduct and safety',
    icon: '🔒',
    items: [
      { value: 'security', label: 'Security' },
      { value: 'other', label: 'Something else' },
    ],
  },
];

export const ALL_CATEGORIES = CATEGORY_GROUPS.flatMap((group) => group.items);

export const categoryLabel = (value) =>
  ALL_CATEGORIES.find((item) => item.value === value)?.label || value;
