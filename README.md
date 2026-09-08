# HKHC Community Discussion Platform

A production-grade, secure, moderated community discussion platform designed specifically for a church community. The platform empowers teenagers, youths, and adults with a psychologically safe space to ask difficult, sensitive, and embarrassing questions—covering faith doubts, mental health, relationships, purity, and family struggles—either under their public community identity or anonymously, without fear of judgment.

---

## Table of Contents

1. [Core Product Philosophy](#core-product-philosophy)
2. [Architectural Overview](#architectural-overview)
3. [The Anonymity & Privacy Model](#the-anonymity--privacy-model)
4. [Database Schema & Data Modeling](#database-schema--data-modeling)
5. [Safety, Moderation & Audit System](#safety-moderation--audit-system)
6. [Security Engineering & Threat Defenses](#security-engineering--threat-defenses)
7. [Local Development Quickstart](#local-development-quickstart)
8. [Automated Test Suite](#automated-test-suite)
9. [PythonAnywhere Production Deployment Guide](#pythonanywhere-production-deployment-guide)
10. [Alternative Production Deployment Options](#alternative-production-deployment-options)
11. [Production Verification Checklist](#production-verification-checklist)
12. [List of Implemented Features](#list-of-implemented-features)
13. [Known Limitations & Future Roadmap](#known-limitations--future-roadmap)

---

## 1. Core Product Philosophy

In church communities, individuals often feel pressure to project perfection, certainty, and happiness. Teenagers and youths navigating deep personal doubts, temptations, family trauma, anxiety, or relationship questions frequently refrain from speaking to pastors or peers because of social vulnerability and fear of stigma.

**HKHC Community Platform** is structured not as an undifferentiated, ephemeral chat room (like Telegram or Discord), but as an **intentional, structured question-and-answer forum with threaded discussions**.

Key Principles:
- **Per-Post Anonymity**: Anonymity is not an account-wide setting. The system asks the user before every single submission: *"How would you like to post? (Post with my identity OR Post anonymously)"*. A member can post a sensitive question anonymously, answer an encouraging Bible question with their real name, and follow up in another room anonymously.
- **Truthful Privacy (Not Absolute Secrecy)**: Anonymity is guaranteed against fellow members, peers, and search engines. However, in keeping with church safeguarding standards, the internal author ID is securely linked in the database and visible only to authorized pastoral moderators when investigating abuse, threats, self-harm, or harassment.
- **Question → Answers → Discussion UX**: Discussion threads clearly distinguish the core question from answers, threaded replies, and constructive debates.

---

## 2. Architectural Overview

The application is built as a **modular Django monolith** adhering to high engineering standards. It avoids the operational fragility of microservices and detached single-page applications.

```
HKHC-Chat-SYSTEM/
├── config/                  # Django project configuration
│   ├── settings/
│   │   ├── base.py          # Shared settings, logging, middleware, auth rules
│   │   ├── development.py   # Local dev overrides (console email, debug)
│   │   └── production.py    # Hardened production settings (HTTPS, HSTS, secure cookies)
│   ├── urls.py              # Root routing and custom HTTP error handlers
│   ├── wsgi.py              # Standard WSGI entrypoint
│   └── asgi.py              # ASGI entrypoint
├── apps/                    # Core business domain modules
│   ├── accounts/            # Custom User model, Profile, authentication, middleware
│   ├── discussions/         # Topics, Discussion threads, Threaded Replies, Bookmarks
│   ├── moderation/          # Reports, Moderator Dashboard, Sanctions, Audit Log
│   ├── notifications/       # In-app notifications & unread badges
│   └── core/                # Sanitization utils, context processors, legal views
├── templates/               # Server-rendered semantic HTML templates
│   ├── accounts/            # Login, registration, profile, password reset templates
│   ├── discussions/         # Topic listing, thread views, reply partials
│   ├── moderation/          # Mod hub, review queue, sanctions, audit logs
│   ├── notifications/       # User notification center
│   ├── core/                # Landing, search, guidelines, privacy policy
│   ├── errors/              # 400, 403, 404, 429, 500 error templates
│   └── base.html            # Core layout with HTMX integration
├── static/                  # Static assets
│   ├── css/style.css        # Clean, accessible, calm church community design system
│   ├── js/app.js            # Vanilla JS for CSRF headers, auto-scroll, interactions
│   └── js/htmx.min.js       # Lightweight dynamic interaction library
├── tests/                   # Real automated test suite (51 comprehensive tests)
├── requirements/            # Layered requirements (base.txt, dev.txt, prod.txt)
├── deploy_pythonanywhere.sh  # Automated production deployment script
├── pythonanywhere_wsgi.py   # PythonAnywhere web app WSGI file
└── manage.py
```

### Frontend Technology
- Primary rendering engine: **Django Templates**
- Dynamic live updates: **HTMX** (submitting replies, fetching unread notification badges, toggling bookmarks without full-page reloads)
- Styles: Custom, accessible CSS with cohesive tokens, responsive layouts, clear visual hierarchy, and mobile-first typography.

---

## 3. The Anonymity & Privacy Model

The application strictly separates **Public Identity** from **Internal Account Identity**:

```
+-------------------------------------------------------------------------------+
|                             AUTHENTICATED USER                                |
|  Internal ID: 42 | Email: teen@example.com | Display Name: Daniel K.           |
+-------------------------------------------------------------------------------+
                                      |
                      Per-Post Anonymity Decision
                                      |
         +----------------------------+----------------------------+
         |                                                         |
[identified]                                                [anonymous]
         |                                                         |
         v                                                         v
+-----------------------------+               +----------------------------------+
| Database Record:            |               | Database Record:                 |
| author_id: 42               |               | author_id: 42                    |
| is_anonymous: False         |               | is_anonymous: True               |
+-----------------------------+               +----------------------------------+
         |                                                         |
         v                                                         v
+-----------------------------+               +----------------------------------+
| Member Presentation:        |               | Member Presentation:             |
| Name: "Daniel K."           |               | Name: "Anonymous Member"         |
| Avatar: User Avatar         |               | Avatar: Neutral Lock Icon        |
| Profile Link: /member/42/   |               | Profile Link: Hidden / Redacted  |
+-----------------------------+               +----------------------------------+
                                                                   |
                                              +--------------------+---------------------+
                                              |                                          |
                                              v                                          v
                                   [Ordinary Member View]                      [Moderator View]
                                   "Anonymous Member"           "Anonymous Member [Mod View: Daniel K. (teen@example.com)]"
```

### Privacy Guarantees
1. **Zero Frontend Leaks**: When `is_anonymous=True`, the author's name, email, avatar, and user ID are strictly scrubbed from HTML responses, data attributes, API payloads, and URLs.
2. **Server-Side Validation**: Anonymity flags cannot be tampered with via request manipulation. If an invalid `post_mode` is passed, the form rejects the request with an explicit validation error.
3. **Database Integrity**: Posts are always attributed to the real authenticated `author_id` in the database. Dummy/ghost accounts are never created.
4. **Pastoral Accountability**: Church moderators can see an inspection banner on anonymous posts to ensure members can be protected from harassment, abuse, or self-harm.

---

## 4. Database Schema & Data Modeling

### Core Models & Relationships

- **`User`** (`apps.accounts.models.User`)
  - Extends `AbstractBaseUser`, `PermissionsMixin`
  - Fields: `email` (unique, used for authentication), `display_name` (public name), `role` (`member`, `moderator`, `administrator`), `status` (`active`, `suspended`, `banned`), `suspension_reason`, `suspended_until`.
- **`Profile`** (`apps.accounts.models.Profile`)
  - One-to-One with `User`
  - Fields: `bio`, `avatar` (secure image upload).
- **`Topic`** (`apps.discussions.models.Topic`)
  - Discussion rooms (e.g., *Faith & Spiritual Life*, *Youth Questions*, *Mental & Emotional Struggles*, *Sexuality & Boundaries*, *Marriage & Family*).
  - Fields: `name`, `slug` (unique), `description`, `icon`, `order`, `is_archived`.
- **`Discussion`** (`apps.discussions.models.Discussion`)
  - Question/thread started in a topic.
  - Fields: `topic`, `author`, `title`, `content`, `is_anonymous`, `status` (`active`, `locked`, `hidden`), `is_deleted`, `deleted_at`, `deleted_by`, `views_count`, `last_activity_at`.
  - Database Indexes: `['topic', '-last_activity_at']`, `['author', '-created_at']`.
- **`Reply`** (`apps.discussions.models.Reply`)
  - Answers and nested replies supporting threaded discussion.
  - Fields: `discussion`, `parent` (Self-referential FK for nesting), `author`, `content`, `is_anonymous`, `status` (`active`, `hidden`), `is_deleted`, `deleted_at`, `deleted_by`.
  - Database Index: `['discussion', 'parent', 'created_at']`.
- **`Bookmark`** (`apps.discussions.models.Bookmark`)
  - User discussion bookmarks. Unique constraint on `['user', 'discussion']`.
- **`Report`** (`apps.moderation.models.Report`)
  - Target polymorphic relations: `target_discussion`, `target_reply`, `target_user`.
  - Fields: `reporter`, `category` (`harassment`, `hate_speech`, `sexual_inappropriate`, `threats`, `spam`, `misinformation`, `self_harm`, `other`), `description`, `status` (`pending`, `under_review`, `resolved`, `dismissed`), `reviewed_by`, `resolution_note`.
- **`AuditLog`** (`apps.moderation.models.AuditLog`)
  - Immutable audit trail of pastoral/moderator decisions.
  - Fields: `moderator`, `action`, `target_repr`, `target_user`, `reason`, `metadata`, `created_at`.
- **`Notification`** (`apps.notifications.models.Notification`)
  - In-app notification center.
  - Fields: `recipient`, `notification_type` (`reply_question`, `reply_comment`, `bookmark_update`, `moderation`), `title`, `message`, `link`, `is_read`.
  - Database Index: `['recipient', 'is_read', '-created_at']`.

---

## 5. Safety, Moderation & Audit System

### Multi-Tiered Safety Mechanism
1. **User Reporting**:
   - Any member can report a question, reply, or user.
   - Built-in duplicate prevention stops report flooding.
   - Distinct categories: Harassment, Inappropriate Content, Spam, Self-Harm, Misinformation, etc.
2. **Dedicated Moderator Hub** (`/moderation/dashboard/`):
   - Real-time community health statistics (total users, active discussions, anonymous posts, pending reports).
   - Filterable report triage queue.
   - Detailed inspection interface revealing internal author identity for flagged anonymous posts.
3. **Pastoral Moderation Actions**:
   - **Content Actions**: Hide content, restore content, lock discussion threads.
   - **User Sanctions**: Issue formal warning, temporary suspension (1, 3, 7, 30 days), or permanent ban.
4. **Session Termination Middleware** (`apps.accounts.middleware.AccountStatusMiddleware`):
   - Suspended or banned users are immediately intercepted on their very next HTTP request and ejected from active sessions.
5. **Immutable Audit Trail**:
   - Every moderation decision is logged with timestamp, moderator identity, target object, and rationale.

---

## 6. Security Engineering & Threat Defenses

- **Cross-Site Scripting (XSS)**:
  - User-generated content is strictly sanitized using `apps.core.utils.sanitize_user_input` powered by `bleach`.
  - Permitted HTML tags are whitelisted (`p`, `br`, `strong`, `em`, `blockquote`, `ul`, `ol`, `li`, `a`).
  - Dangerous attributes like `onerror`, `onload`, and `javascript:` URIs are stripped.
  - External links automatically receive `rel="nofollow noopener noreferrer"` and `target="_blank"`.
- **Cross-Site Request Forgery (CSRF)**:
  - Enforced on all POST forms.
  - `apps/static/js/app.js` configures HTMX to automatically inject `X-CSRFToken` into every asynchronous request.
- **Insecure Direct Object References (IDOR)**:
  - Edit and delete views verify ownership server-side (`can_user_edit`, `can_user_delete`).
  - Notification mark-read views strictly filter by `recipient=request.user`.
- **Privilege Escalation Protection**:
  - Forms explicitly exclude `is_staff`, `is_superuser`, and `role`. Attempts to submit elevated roles during registration or profile edits are discarded.
- **N+1 Query Elimination**:
  - Discussion and topic views utilize `select_related('topic', 'author', 'author__profile')` and `annotate()` query counts to maintain constant database query numbers.
- **Production Headers & Cookies**:
  - `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `X_FRAME_OPTIONS = "DENY"`, `SECURE_CONTENT_TYPE_NOSNIFF = True`, `SECURE_BROWSER_XSS_FILTER = True`, and HSTS headers.

---

## 7. Local Development Quickstart

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Git
- SQLite (included with Python) or PostgreSQL

### 1. Clone & Set Up Virtual Environment

```bash
cd /path/to/desired/directory
git clone <repo-url> HKHC-Chat-SYSTEM
cd HKHC-Chat-SYSTEM

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
```

Review `.env`: For local development, `DEBUG=True` and SQLite database are configured by default.

### 4. Run Migrations & Seed Community Data

```bash
# Apply database migrations
python manage.py migrate

# Seed 10 church discussion topics and sample test accounts
python manage.py seed_community_data
```

### 5. Pre-Configured Test Accounts

The seed script creates the following ready-to-test accounts:

| Role | Email | Password | Description |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@hkhc.org` | `AdminPass123!` | Full admin & moderator permissions, Django admin access |
| **Moderator** | `moderator@hkhc.org` | `ModeratorPass123!` | Access to Moderator Dashboard, reports, and sanction tools |
| **Member 1** | `daniel@example.com` | `MemberPass123!` | Youth community member |
| **Member 2** | `sarah@example.com` | `MemberPass123!` | Adult community member |

To create an additional custom superuser:
```bash
python manage.py createsuperuser
```

### 6. Start Development Server

```bash
python manage.py runserver
```

Open your browser at `http://127.0.0.1:8000`.

---

## 8. Automated Test Suite

The test suite covers authentication, role authorization, privacy/anonymity guarantees, discussion workflows, moderation, notification dispatch, search, security hardening, and database query optimization.

Run all tests:
```bash
python manage.py test
```

Run with verbose reporting:
```bash
python manage.py test -v 2
```

Run specific test modules:
```bash
python manage.py test tests.test_anonymity
python manage.py test tests.test_authentication
python manage.py test tests.test_authorization
python manage.py test tests.test_discussions
python manage.py test tests.test_moderation
python manage.py test tests.test_notifications
python manage.py test tests.test_search
python manage.py test tests.test_security
python manage.py test tests.test_performance
```

---

## 9. PythonAnywhere Production Deployment Guide

PythonAnywhere is the primary deployment target for this church community. Follow these step-by-step instructions:

### Step 1: Push Code to Git & Clone into PythonAnywhere
In your PythonAnywhere account, open a **Bash Console**:

```bash
# Clone the repository
git clone https://github.com/your-username/HKHC-Chat-SYSTEM.git /home/yourusername/HKHC-Chat-SYSTEM
cd /home/yourusername/HKHC-Chat-SYSTEM

# Create virtual environment
python3.11 -m venv /home/yourusername/.virtualenvs/hkhc-env
source /home/yourusername/.virtualenvs/hkhc-env/bin/activate

# Install production dependencies (including psycopg2-binary for PostgreSQL)
pip install --upgrade pip
pip install -r requirements/prod.txt
```

### Step 2: Configure Environment Variables
Create `/home/yourusername/HKHC-Chat-SYSTEM/.env`:

```bash
cp .env.example .env
nano .env
```

Set the production variables:
```ini
SECRET_KEY=your-long-random-production-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com,community.yourchurch.org
CSRF_TRUSTED_ORIGINS=https://yourusername.pythonanywhere.com,https://community.yourchurch.org

# Database Configuration (PythonAnywhere Postgres or SQLite)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=yourusername$hkhc_community_db
DB_USER=yourusername
DB_PASSWORD=your_postgres_password
DB_HOST=yourusername-1234.postgres.pythonanywhere-services.com
DB_PORT=5432

# Email Provider (e.g. SendGrid or Amazon SES)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your_sendgrid_api_key
DEFAULT_FROM_EMAIL=HKHC Community <noreply@yourchurch.org>

# HTTPS Cookies
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

### Step 3: Run Database Migrations & Collect Static Files
Execute the automated deployment helper:

```bash
./deploy_pythonanywhere.sh
```

Or run the individual commands:
```bash
python manage.py migrate --settings=config.settings.production
python manage.py seed_community_data --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
```

### Step 4: PythonAnywhere Web App Configuration
Navigate to the **Web** tab on the PythonAnywhere Dashboard:
1. Click **Add a new web app**.
2. Select **Manual configuration** and choose **Python 3.11** (or 3.10/3.12).
3. Set **Virtualenv path**:
   `/home/yourusername/.virtualenvs/hkhc-env`
4. Set **Source code path**:
   `/home/yourusername/HKHC-Chat-SYSTEM`
5. Set **Working directory**:
   `/home/yourusername/HKHC-Chat-SYSTEM`

### Step 5: Configure the WSGI File
Click on the **WSGI configuration file** link (e.g. `/var/www/yourusername_pythonanywhere_com_wsgi.py`). Delete the default contents and replace with:

```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path("/home/yourusername/HKHC-Chat-SYSTEM")
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

APPS_DIR = PROJECT_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# Load .env
load_dotenv(PROJECT_DIR / ".env")

# Set Django production settings
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.production"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 6: Map Static and Media Directories
In the **Static files** section of the Web tab, configure two directory mappings:

| URL | Directory |
| :--- | :--- |
| `/static/` | `/home/yourusername/HKHC-Chat-SYSTEM/staticfiles` |
| `/media/` | `/home/yourusername/HKHC-Chat-SYSTEM/media` |

### Step 7: Reload the Web App
Click the big green **Reload yourusername.pythonanywhere.com** button at the top of the Web tab. Your application is live!

---

## 10. PythonAnywhere Tier Considerations & Alternatives

### PythonAnywhere Capabilities & Limitations

| Feature | Free "Beginner" Tier | "Hacker" / Custom Paid Tier (~$5/mo) |
| :--- | :--- | :--- |
| **Domain** | Subdomain only (`username.pythonanywhere.com`) | Custom domain support (`community.yourchurch.org`) |
| **HTTPS** | Let's Encrypt / Wildcard subdomains | Free automated Let's Encrypt for custom domains |
| **Database** | MySQL / SQLite only (PostgreSQL requires upgrade) | Dedicated PostgreSQL database included |
| **Outbound HTTP** | Whitelist-restricted (cannot send emails via arbitrary SMTP) | Unrestricted outbound HTTP (SendGrid, Mailgun, SES work) |
| **WebSockets** | Not supported | Not supported (WSGI only) |

> [!IMPORTANT]
> **Free Tier Practicality Notice**:
> If running on PythonAnywhere's free tier, you must use **SQLite** (or MySQL) and SendGrid's API via allowed endpoints, and the URL will be `username.pythonanywhere.com`.
> For a true church production rollout with a custom domain (`community.church.org`), transactional emails, and PostgreSQL, PythonAnywhere's least-expensive tier (~$5/month) or an alternative PaaS is required.

### Alternative Production Options
The codebase is a standard WSGI Django monolith, meaning it can be deployed with zero code modifications to:
- **Render / Railway / Fly.io**: Supports PostgreSQL, automatic HTTPS, and environment secrets out of the box.
- **Ubuntu VPS (DigitalOcean / Linode / Hetzner)**: Using Nginx + Gunicorn + Systemd + Certbot.

---

## 11. Production Verification Checklist

Before opening the platform to the church congregation, confirm:

- [x] **Registration & Authentication**: Sign up with email, login, logout, password reset flow.
- [x] **Anonymity Verification**: Ordinary member viewing an anonymous post sees "Anonymous Member" and zero references to the author's display name, email, or user ID.
- [x] **Moderator De-Anonymization**: Authorized moderator viewing the same post sees the pastoral inspection banner with real author details.
- [x] **Topic Rooms**: All 10 pastoral categories seeded, active, and navigable.
- [x] **Threaded Discussions**: Asking a question, posting an answer, and writing a nested reply.
- [x] **Live Interactivity**: HTMX dynamically appends replies and updates notification badges without full page reloads.
- [x] **Reporting & Triage**: Submitting reports on questions, replies, and user profiles; resolving reports in the Moderator Hub.
- [x] **Sanctions Enforcement**: Warnings, suspensions, and bans immediately enforced by middleware.
- [x] **Audit Trail**: Every moderator action creates an immutable audit log.
- [x] **In-App Notifications**: Unread badges update; clicking notification marks it as read.
- [x] **Search Engine**: Searching topics, titles, and discussion contents respects anonymity and excludes hidden content.
- [x] **Performance & N+1 Prevention**: Query counts bounded and verified by automated tests.
- [x] **Security Hardening**: `DEBUG=False` in production, CSRF enforced, XSS stripped, IDOR rejected, secure cookies configured.
- [x] **Automated Tests**: All 51 automated tests passing.

---

## 12. List of Implemented Features

1. **Custom Authentication & Profiles**: Email-based authentication, unique display names, avatar upload, password reset, account status tracking.
2. **Topic-Based Discussion Rooms**: Faith, youth, mental health, sexuality, marriage, and church life categories with admin management.
3. **Structured Discussion UX**: Question → Answers → Nested debate replies.
4. **Independent Per-Post Anonymity**: User chooses identified or anonymous mode before every post; clear explainer banner displayed.
5. **Pastoral Moderation Hub**: Comprehensive dashboard with community stats, report queues, content inspection, and user sanctions.
6. **Account Status Middleware**: Real-time ejection of suspended/banned users.
7. **In-App Notification Center**: Instant notifications for question answers, comment replies, and followed discussion updates.
8. **Community Search**: Title, content, and topic search with pagination and privacy safeguards.
9. **Bookmarks**: Follow threads to receive real-time updates.
10. **Custom Error Handling**: Polished, accessible 400, 403, 404, 429, and 500 error pages.

---

## 13. Known Limitations & Future Roadmap

### Current Version Design Scope
- **Text-Centric Discussions**: Version 1 focuses deliberately on text-based discussions without arbitrary file attachments, protecting teenagers from inappropriate image uploads and minimizing hosting storage requirements.
- **Polling vs WebSockets**: HTMX polling (45-second intervals) is utilized for notification badges and reply counts to ensure 100% compatibility with PythonAnywhere's WSGI server without requiring Redis or Daphne.

### Recommended Future Enhancements
1. **Pastoral Direct Messaging / Private Pastoral Care**: A dedicated pastoral help request button allowing a member to transition a sensitive anonymous question into a confidential 1-on-1 private counseling thread with an ordained pastor.
2. **Scheduled Scripture & Devotional Highlights**: Ability for pastoral staff to pin devotionals and discussion prompts at the top of specific topic rooms each week.
3. **Daily / Weekly Email Digest**: Optional email summary of discussions in followed topic rooms.
4. **Two-Factor Authentication (2FA)**: Time-based One-Time Password (TOTP) 2FA for moderators and administrators.
