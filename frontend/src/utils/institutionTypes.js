/**
 * The institution types, in one place.
 *
 * Must match INSTITUTION_TYPES in backend/app/models/institution.py.
 * These drifted apart once already: the admin form wrote 'college' while
 * the imported register wrote 'college_of_education', so filtering by
 * either silently hid the other. Two screens then kept their own partial
 * copies of the labels, which is how the drift went unnoticed.
 */
export const INSTITUTION_TYPES = [
  { value: 'university', label: 'University' },
  { value: 'polytechnic', label: 'Polytechnic' },
  { value: 'college_of_education', label: 'College of education' },
  { value: 'teaching_hospital', label: 'Teaching hospital' },
  { value: 'agency', label: 'Government agency' },
];

const LABELS = Object.fromEntries(INSTITUTION_TYPES.map((t) => [t.value, t.label]));

/** A readable label, falling back to whatever the server sent. */
export const institutionTypeLabel = (value) => LABELS[value] || value || '';
