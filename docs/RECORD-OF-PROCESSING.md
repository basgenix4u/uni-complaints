# Record of Processing Activities

**Draft for legal review.**

> Required for NDPC registration and to demonstrate accountability under the
> Nigeria Data Protection Act 2023. Prepared by the engineering team from
> what the software actually does. A data protection practitioner should
> confirm the lawful bases and complete the bracketed sections.

**Controller:** _[registered name]_ · **Prepared:** 2026-09-18 · **Review:** annually

---

## 1. Identity

| Field | Value |
|---|---|
| Controller | _[institution or operating company]_ |
| Registration number | _[CAC number]_ |
| Address | _[address]_ |
| Data Protection Officer | _[name, email, phone]_ |
| DCPMI status | _[to be assessed against NDPC thresholds by volume of data subjects]_ |

---

## 2. Processing activities

### A. Account management

| | |
|---|---|
| Purpose | Allow students and staff to sign in and be identified |
| Data subjects | Students, institution staff |
| Categories | Name, email, matric number, faculty, department, phone, password hash, role, sign-in timestamps |
| Lawful basis | Contract (NDPA s.25) |
| Recipients | Institution administrators |
| Retention | Until erasure is requested, or the institution's period expires |
| Transfers | _[hosting region]_ |
| Security | bcrypt hashing, TLS, role checks enforced server side, rate limited sign-in |

### B. Complaint handling

| | |
|---|---|
| Purpose | Receive complaints, route them, record decisions |
| Data subjects | Students, and any person named in a complaint |
| Categories | Complaint text, category, priority, status, timestamps, messages, attachments |
| **Special category risk** | A complaint may disclose health, religion or an allegation of misconduct. This is unavoidable in free text and is treated as sensitive |
| Lawful basis | Contract; legitimate interest of the institution in handling grievances |
| Recipients | Assigned officer, department head, institution administrators |
| Retention | Institution-defined period after closure; then automatic deletion |
| Security | Tenant isolation at query level, private notes hidden from students, file type verification, files outside the web root |

> **Third-party data.** A complaint often names a member of staff who has
> not consented. This is processed under the institution's legitimate
> interest in investigating grievances. _[Confirm the institution's
> disciplinary policy covers notifying named individuals.]_

### C. Notification

| | |
|---|---|
| Purpose | Tell people when their complaint changes |
| Categories | Email address, phone number, message content |
| Lawful basis | Contract |
| Recipients | _[SMTP provider]_, _[SMS provider: Termii or Africa's Talking]_ |
| Retention | Queue rows kept for delivery audit; _[set a period]_ |
| Transfers | Depends on provider. _[Confirm and record the mechanism]_ |

### D. Access logging

| | |
|---|---|
| Purpose | Record which staff opened which complaint |
| Data subjects | Institution staff |
| Categories | Staff identifier, role at time of access, IP address, browser description, timestamp |
| Lawful basis | Legal obligation (accountability); legitimate interest in detecting misuse |
| Recipients | Institution administrators only |
| Retention | _[set a period, commonly 12 to 24 months]_ |

> Student reads are deliberately not logged. Recording ordinary use would
> bury the staff entries that matter and would itself be excessive.

### E. Statistics and reporting

| | |
|---|---|
| Purpose | Show where complaints cluster and whether deadlines are met |
| Categories | Aggregate counts, resolution times; exports may include names |
| Lawful basis | Legitimate interest |
| Recipients | Department heads and above |
| Note | Exports containing personal data are restricted to department head and above, and anonymous complaints export without an author |

### F. Password reset

| | |
|---|---|
| Purpose | Let someone regain access |
| Categories | Email address, token hash, requesting IP |
| Lawful basis | Contract |
| Retention | Tokens expire after one hour and are single use |
| Note | Only a SHA-256 hash of the token is stored, so a stolen backup yields no working links |

---

## 3. Data subject rights, as implemented

| Right | Implementation | Route |
|---|---|---|
| Access and portability (s.39) | Self-service JSON download | `GET /api/privacy/my-data` |
| Erasure (s.37) | Self-service, password confirmed; or by administrator on written request | `POST /api/privacy/erase-my-account` |
| Rectification | Profile editing | `PUT /api/auth/profile` |
| Storage limitation (s.24) | Scheduled purge per institution | `flask purge-expired` |

**Limit on erasure.** Complaints survive as anonymous rows. The personal
data is removed; the institutional record of the decision is kept. This is
disclosed in the privacy policy and in the interface before the user
confirms.

---

## 4. Retention schedule

| Data | Period | Mechanism |
|---|---|---|
| Open complaints | Until closed | — |
| Closed complaints | Institution-defined, default off | `flask purge-expired`, nightly |
| Attachments | With their complaint | Deleted with the row, from disk |
| Access logs | _[to be set]_ | _[not yet implemented — see gaps]_ |
| Outbound message queue | _[to be set]_ | _[not yet implemented — see gaps]_ |
| Reset tokens | 1 hour | Expiry, single use |

---

## 5. Breach procedure

1. Detect, and record what was affected.
2. Assess the risk to the people involved.
3. **Notify the NDPC within 72 hours** where rights are likely to be affected.
4. Notify affected people directly where risk to them is high.
5. Record the incident, the decision and the reasoning.

_[Assign an owner for each step. Steps 3 to 5 are organisational, not
software.]_

---

## 6. Known gaps

Recorded openly rather than left implicit.

| Gap | Status |
|---|---|
| Retention for access logs and message queue | Not implemented; complaints are covered |
| Breach detection | Manual. No automated alerting yet |
| DPIA | Not produced. Likely required given allegations about identifiable staff |
| DPO | Not appointed |
| NDPC registration | Not assessed against DCPMI thresholds |
| Cross-border transfer mechanism | Depends on final hosting choice |

The first item is code and can be built. The rest are organisational
decisions for the controller.
