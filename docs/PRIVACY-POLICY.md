# Privacy Policy

**Draft for legal review. Not yet in force.**

> This document was prepared by the engineering team to describe accurately
> what the software does with personal data. It has **not** been reviewed by
> a lawyer. Before publishing, a Nigerian data protection practitioner
> should check it against the Nigeria Data Protection Act 2023 and insert
> the operator's own details in the marked places.

**Last updated:** _[date]_
**Data controller:** _[registered name of the institution or operating company]_
**Contact:** _[email]_
**Data Protection Officer:** _[name and contact, once appointed]_

---

## 1. What this covers

This policy explains what happens to personal data when you use Resolve to
file or handle a complaint at your institution.

Your institution is the **data controller** for complaints filed by its own
students and staff. _[Operating company]_ provides and runs the software as
a **data processor** on the institution's instructions.

---

## 2. What we collect

### When you create an account
Name, email address, matric number, faculty, department, and phone number
if you provide one. A password is never stored; only a bcrypt hash of it is
kept.

### When you file a complaint
The category, title and description you write, the priority you choose, any
files you attach, and the messages you exchange with staff afterwards.

### Automatically
The date and time of each action, and the IP address and browser
description recorded when a member of staff opens a complaint. That last
record exists so an institution can answer who looked at a case.

### We do not collect
We do not use tracking cookies, advertising identifiers, or third-party
analytics. We do not sell data to anyone, under any circumstances.

---

## 3. Why we hold it, and on what basis

| What we do | Why | Lawful basis (NDPA s.25) |
|---|---|---|
| Create and maintain your account | So you can sign in and track your complaints | Contract |
| Receive and route complaints | To get your complaint to the right department | Contract; legitimate interest of the institution |
| Send email and SMS about your complaint | To tell you when something changes | Contract |
| Record who opened a complaint | Accountability, and investigating misuse | Legal obligation; legitimate interest |
| Produce statistics | To help the institution see where problems cluster | Legitimate interest, using anonymised data |
| Keep records after a complaint closes | Institutional and regulatory record keeping | Legal obligation |

Where your complaint reveals something sensitive, such as a health matter
or an allegation of misconduct, we handle it only as far as is necessary to
resolve it, and only the staff handling it can see it.

---

## 4. Who can see your data

- **You.** Everything about your own complaints.
- **Staff handling your complaint.** The officer assigned, their department
  head, and institution administrators.
- **Nobody at another institution.** Data is separated by institution at the
  database level, and a request that crosses that line is refused.
- **Other students.** Never.

Internal notes written by staff are not visible to you. They are the
institution's own deliberation. Equally, they are excluded from the copy of
your data you can download, because they are not personal data about you.

### Anonymous complaints
Where your institution allows it, you may file without attaching your name.
The author is then hidden from staff as well, and stays hidden in exports
and statistics.

---

## 5. Where it is kept

Data is stored on servers operated by _[hosting provider, region]_.

If that is outside Nigeria, the transfer relies on _[adequacy decision,
standard contractual clauses, or your chosen mechanism]_ as required by
Part IX of the NDPA.

Email and SMS are delivered by _[provider names]_, who see only the
recipient address and the message content.

---

## 6. How long we keep it

Each institution sets its own retention period. When a complaint has been
closed for longer than that period, it and its attachments are deleted
automatically.

If no period is set, records are kept until the institution sets one or you
ask for erasure. Institutions are encouraged to set a period; we do not set
one on their behalf.

---

## 7. Your rights

Under the NDPA you may:

| Right | How to use it |
|---|---|
| **Access and portability** (s.39) | Sign in and use *Your data → Download my data*. You get a JSON file containing everything. |
| **Erasure** (s.37) | Sign in and use *Your data → Erase my data*, or write to your institution. |
| **Rectification** | Correct your details on your profile page, or ask an administrator. |
| **Object or restrict** | Write to the contact above. |
| **Complain to the regulator** | Nigeria Data Protection Commission, if you are unhappy with our response. |

### What erasure actually does
Your name, email, matric number, phone, uploaded files, notifications and
everything you wrote are removed permanently.

Complaints you filed are **kept as anonymous records**, because they are
also the institution's account of what was reported and what it decided.
After erasure nothing in them points back to you.

We are explicit about this because it is a real limit on the right, and you
should know it before you ask.

---

## 8. How it is protected

- Passwords hashed with bcrypt; never stored or recoverable in plain text.
- All traffic encrypted in transit.
- Access is role based and enforced on the server, not merely hidden in the
  interface.
- Uploaded files are stored outside the web root and served only to people
  entitled to the complaint. File contents are inspected on upload so a
  program cannot be disguised as an image.
- Sign-in attempts are rate limited.
- Every change to a complaint, and every staff view of one, is recorded.

No system is perfectly secure, and we do not claim otherwise.

---

## 9. If something goes wrong

If a breach occurs that is likely to affect your rights, we will notify the
Nigeria Data Protection Commission **within 72 hours** as s.40 requires, and
tell you directly where the risk to you is high.

---

## 10. Changes

Material changes will be notified by email and announced in the application
before they take effect.

---

## 11. Contact

_[Data Protection Officer name]_
_[email]_ · _[postal address]_ · _[phone]_

If you are not satisfied with our response, you may complain to the Nigeria
Data Protection Commission.
