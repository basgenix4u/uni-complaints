<div align="center">

# 🎓 UniComplaints

**A campus complaint management system for Nigerian universities** — students submit and track complaints; administrators triage, respond, and resolve them with full accountability.

[![Flask](https://img.shields.io/badge/Backend-Flask%203-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/Frontend-React%2018-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![Vite](https://img.shields.io/badge/Build-Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind-38bdf8?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](./LICENSE)

</div>

---

## ✨ Overview

University complaints usually disappear into suggestion boxes, departmental email threads, or verbal promises. **UniComplaints** gives them a home: students file structured complaints and follow their progress, while administrators triage, assign, respond, and close the loop — with every action recorded.

---

## 👥 Roles

| Role | Capabilities |
| --- | --- |
| **Student** | Register, log in, file a complaint, track status, view responses, manage notifications and profile |
| **Admin** | Dashboard and analytics, triage all complaints, respond, manage users, configure settings |

---

## 🚀 Features

### 🎓 Student
- Register and log in with JWT authentication
- **File a complaint** with category, priority, and attachments
- Track complaint status end to end
- Read official responses and updates
- Notifications on status changes
- Profile management

### 🛡️ Admin
- **Executive dashboard** with KPI cards and analytics
- Full complaint queue with filtering
- **Complaint detail** with response thread and internal notes
- User management
- Platform settings

### 🧩 Shared
- **Design system** — Button, Card, Badge, Modal, Input, Select, Textarea, Avatar, StatCard, StatusBadge, EmptyState, Spinner, PageHeader
- Animated transitions with Framer Motion
- Responsive layouts down to mobile

---

## 🛠 Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3, Flask 3, SQLAlchemy 2, Flask-Migrate |
| Auth | Flask-JWT-Extended, Flask-Bcrypt, PyJWT |
| Database | PostgreSQL (SQLite for local dev) |
| Frontend | React 18, Vite, Tailwind CSS |
| Data fetching | Axios + TanStack Query |
| State | Zustand |
| Forms | React Hook Form + Zod |
| UI | Headless UI, Heroicons, Lucide, Framer Motion |
| CI | GitHub Actions |

---

## ⚡ Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask run
# → http://localhost:5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 📁 Project Structure

```text
uni-complaints/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models (User, Complaint, Response)
│   │   ├── routes/          # Blueprints
│   │   └── extensions.py    # db, jwt, bcrypt, migrate
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── auth/        # Login, Register
│       │   ├── student/     # Dashboard, New/My Complaints, Details, Notifications, Profile
│       │   └── admin/       # Dashboard, Complaints, Analytics, Users, Settings
│       ├── components/      # ui · layout · shared
│       ├── services/api.js  # Axios client
│       └── stores/          # Zustand auth store
└── .github/workflows/       # CI (Flask + Vite)
```

---

## 📜 Available Scripts

### Frontend

| Command | Description |
| --- | --- |
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Production build |
| `npm run preview` | Preview the production build |
| `npm run lint` | Run ESLint |

---

## 🔐 Security

- Passwords hashed with **bcrypt**
- Stateless **JWT** access tokens
- Role checks enforced server-side on admin routes
- CORS restricted to configured origins

---

## 🗺 Roadmap

- [ ] Complaint categories and SLA configuration
- [ ] Email notifications
- [ ] File attachment storage
- [ ] Escalation workflow
- [ ] End-to-end test suite

---

## 📄 License

Released under the [MIT License](./LICENSE).

---

<div align="center">

Built by [Abdulbasit Abdulalim](https://github.com/basgenix4u)

</div>
