# Production Readiness — Honest Gap Analysis

**Date:** 2026-09-18 · **Status of build:** 118 backend tests, 52 browser journeys, 53 API routes, CI green

The software works. That is not the same as being ready to take real complaints from real students at a real institution. This is what is actually left, separated by whether it is a legal requirement, an operational necessity, or a preference.

---

## 1. 🔴 Legal — blocks launch, not optional

Running this in Nigeria makes you a **data controller** under the **Nigeria Data Protection Act 2023**. Complaints contain names, matric numbers, and often allegations about named staff. That is squarely personal data, and some of it is sensitive.

### What the law requires that we do not have

| Requirement | NDPA reference | Current state |
|---|---|---|
| Published privacy policy | s.27 transparency | ✗ none |
| Lawful basis stated per processing activity | s.25 | ✗ none |
| Right to erasure | s.37 | ✗ no way to delete an account |
| Right to data portability | s.39 | ✗ students cannot export their own data |
| Breach notification within 72 hours | s.40 | ✗ no detection, no procedure |
| Record of Processing Activities (ROPA) | registration requirement | ✗ none |
| Data Protection Impact Assessment | s.29, high-risk processing | ✗ none |
| Retention schedule | s.24(d) storage limitation | ✗ data kept forever |
| Data Protection Officer | s.31 | ✗ not appointed |

### Penalty exposure

Up to **₦10,000,000 or 2% of annual gross revenue**, whichever is greater, for a controller of major importance — and **₦2,000,000 or 2%** otherwise. Criminal prosecution is available for wilful or negligent mishandling.

### Whether registration applies to you

Registration with the NDPC is mandatory only for a **Data Controller of Major Importance (DCPMI)**, determined by thresholds on the volume of data subjects. A single pilot department will likely fall below it. **An operator holding records for several universities almost certainly will not** — and that is the stated ambition.

Either way, the general obligations above apply from the first real student record, regardless of registration status.

### What I can build, and what I cannot

I can implement: erasure, export, retention jobs, breach detection and logging, access auditing, and draft the privacy policy and ROPA.

I cannot: appoint a DPO, register with the NDPC, or sign off a DPIA. Those are decisions for you, and for a Nigerian data protection lawyer. **Do not treat this document as legal advice.**

---

## 2. 🔴 Operational — will cause an incident

### No observability
There is no structured logging, no request correlation ID, and no error tracking. When a registrar says *"I submitted a complaint yesterday and it vanished"*, there is currently no way to answer them. Logs are unstructured lines on one container.

### No deployment pipeline
There is a Dockerfile and no deploy workflow, no environment definitions, no rollback. Every release is manual, which is how the wrong build reaches production at 2am.

### No backups
Nothing documents how the database is backed up, how often, where it is stored, or — the part people skip — **whether a restore has ever been tested**. An untested backup is a hope, not a backup.

### Rate limiting needs Redis
Already enforced at boot: production refuses to start with in-memory counters and multiple workers. But that means **production cannot start at all until Redis exists**. That is a deployment dependency, not a code task.

### Uploads need real storage
Files write to a local directory. On most container hosts that disappears on redeploy. Needs object storage, or a guaranteed persistent volume.

### No access auditing
The audit trail records every write. It does not record **reads**. For a system where a complaint may name a member of staff, *"which officers opened this complaint"* is a question an institution will eventually have to answer, possibly in a disciplinary context.

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

## Suggested order

| Phase | Work | Why this order |
|---|---|---|
| **A** | Privacy policy, ROPA, erasure, export, retention, access audit | Legal exposure starts with the first real record |
| **B** | Structured logs, request IDs, error tracking, deploy workflow, backup and restore drill | You cannot safely run what you cannot observe |
| **C** | Redis, object storage, staging environment | Deployment dependencies |
| **D** | One pilot department, 50 complaints, one week | Everything after this should be driven by what it teaches |
| **E** | Bulk import, SSO, email templates | Scale-up, informed by the pilot |

---

## The honest summary

The engineering is in reasonable shape. **What is missing is mostly not code** — it is legal groundwork, operational infrastructure, and evidence from real use.

The single biggest risk is not a bug. It is launching without the data protection groundwork, because the penalty is financial and the exposure begins the moment the first student files a real complaint.
