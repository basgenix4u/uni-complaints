# Production Readiness — Honest Gap Analysis

**Date:** 2026-09-20 · **Status of build:** 152 backend tests, 52 browser journeys, 58 API routes, CI green

> **Update.** Phases A and B are complete. What remains below is either a
> decision for the controller, a dependency to provision, or evidence that
> only real use can produce. The software side of launch is done.

The software works. That is not the same as being ready to take real complaints from real students at a real institution. This is what is actually left, separated by whether it is a legal requirement, an operational necessity, or a preference.

---

## 1. 🔴 Legal — blocks launch, not optional

Running this in Nigeria makes you a **data controller** under the **Nigeria Data Protection Act 2023**. Complaints contain names, matric numbers, and often allegations about named staff. That is squarely personal data, and some of it is sensitive.

### What the law requires

| Requirement | NDPA reference | State |
|---|---|---|
| Published privacy policy | s.27 transparency | ✓ drafted, needs legal review |
| Lawful basis per processing activity | s.25 | ✓ recorded in the ROPA |
| Right to erasure | s.37 | ✓ built, self-service and by administrator |
| Right to data portability | s.39 | ✓ built, JSON download |
| Retention schedule | s.24(d) | ✓ built, per institution, nightly purge |
| Accountability for access | s.24 | ✓ built, every staff view recorded |
| Record of Processing Activities | registration | ✓ drafted, needs legal review |
| Breach notification within 72 hours | s.40 | ◑ procedure written, detection is manual |
| Data Protection Impact Assessment | s.29 | ✗ yours — a practitioner must produce it |
| Data Protection Officer | s.31 | ✗ yours — an appointment, not code |
| NDPC registration | s.44 | ✗ yours — assess against DCPMI thresholds |

### Penalty exposure

Up to **₦10,000,000 or 2% of annual gross revenue**, whichever is greater, for a controller of major importance — and **₦2,000,000 or 2%** otherwise. Criminal prosecution is available for wilful or negligent mishandling.

### Whether registration applies to you

Registration with the NDPC is mandatory only for a **Data Controller of Major Importance (DCPMI)**, determined by thresholds on the volume of data subjects. A single pilot department will likely fall below it. **An operator holding records for several universities almost certainly will not** — and that is the stated ambition.

Either way, the general obligations above apply from the first real student record, regardless of registration status.

### What I can build, and what I cannot

I can implement: erasure, export, retention jobs, breach detection and logging, access auditing, and draft the privacy policy and ROPA.

I cannot: appoint a DPO, register with the NDPC, or sign off a DPIA. Those are decisions for you, and for a Nigerian data protection lawyer. **Do not treat this document as legal advice.**

---

## 2. Operational

| Item | State |
|---|---|
| Structured logging with request tracing | ✓ built. Every response carries `X-Request-ID`; errors return it as a quotable reference |
| Error reporting | ✓ built. Optional Sentry, bodies and cookies stripped before sending |
| Deployable stack | ✓ built. Compose with PostgreSQL, Redis, API, worker, daily backup |
| Backup and restore drill | ✓ documented in `docs/OPERATIONS.md`, including what the dump omits |
| Access auditing | ✓ built. Every staff view recorded with who, role, when and from where |
| Redis instance | ✗ yours — provision it. Production will not start without it |
| Object storage or a persistent volume | ◑ the compose volume covers a single host. Multiple hosts need object storage |
| Domain, TLS, hosting account | ✗ yours |
| Running the restore drill once | ✗ yours — the procedure is written, someone has to do it |

---

## 3. 🟠 Product — needed before students touch it

### Nobody has used it
Zero real complaints have passed through this. Every routing rule, SLA default and category grouping is my reasoning, not observed behaviour. **The first week of a pilot will invalidate some of it.**

### No bulk onboarding
Students register one at a time. An institution has a student register in a spreadsheet and will expect to import it. There is no import, no invitation flow, and no single sign-on.

### No email templating
Notifications are plain text built in code. An institution will want its letterhead, its wording, and its own sender address.

### Accessibility is asserted, not certified
I verified contrast numerically and tested keyboard paths in 52 journeys. Nobody has run it with a screen reader, and no disabled user has tried it.

---

## 4. 🟡 Preference — genuinely optional

Dark mode, saved filter presets, complaint templates, richer analytics, a mobile app. None of these block anything.

---

## Where things stand

| Phase | Work | State |
|---|---|---|
| **A** | Erasure, export, retention, access audit, policy and ROPA drafts | ✓ done |
| **B** | Structured logs, request tracing, error reporting, compose stack, operations guide | ✓ done |
| **C** | Redis, hosting, domain, TLS, running the restore drill | Yours |
| **D** | Legal review, DPO, DPIA, NDPC assessment | Yours |
| **E** | Pilot, then bulk import and SSO informed by it | After C and D |

---

## What is left, honestly

**Nothing in phases A and B remains as code.** Every obligation that could
be implemented has been, every operational gap that could be closed in
software is closed, and 152 backend tests plus 52 browser journeys cover
it.

What remains splits cleanly:

**Provisioning** — a server, a domain, TLS, a Redis instance, an SMTP
account, an SMS account. These are purchases and configuration.

**Legal** — a practitioner reviewing the two drafts, appointing a DPO,
producing the DPIA, and assessing whether NDPC registration is triggered.
A single pilot department probably falls below the DCPMI threshold; an
operator holding records for several universities will not.

**Evidence** — the restore drill has a written procedure and has never been
run. The accessibility work is verified numerically and by keyboard, but no
screen reader user has tried it. No real complaint has passed through the
system.

The remaining risk is no longer a missing feature. It is that the first
week of real use will contradict some assumption baked into the routing
rules, the SLA defaults or the category grouping — and no amount of further
building will reveal which one.
