# TerrierFit

TerrierFit is a production-oriented Django fitness management application for workout tracking, nutrition logging, hydration monitoring, body metrics, goal management, notifications, and account recovery. The application is implemented as a server-rendered Django monolith with authenticated, per-user data isolation across all primary workflows.

## Table of Contents

- [Project Overview](#project-overview)
- [Core Capabilities](#core-capabilities)
- [Technical Stack](#technical-stack)
- [System Architecture](#system-architecture)
- [Repository Layout](#repository-layout)
- [Configuration](#configuration)
- [Local Development](#local-development)
- [Testing and Quality Gates](#testing-and-quality-gates)
- [External Integrations](#external-integrations)
- [Deployment](#deployment)
- [Security Considerations](#security-considerations)
- [Known Limitations](#known-limitations)

## Project Overview

TerrierFit consolidates the daily fitness workflows required by an individual user into a single web application. It supports account registration, email-based password reset, workout and exercise tracking, nutrition and water intake logging, body measurement history, goal progress calculation, and notification delivery.

The application is designed for straightforward deployment on a single virtual server. It uses Django templates and custom CSS for the user interface, the Django ORM for persistence, and optional third-party APIs for enhanced nutrition and calorie-estimation features.

## Core Capabilities

- Email-first registration with optional username entry.
- Login with either email address or username.
- Password reset through configured SMTP email delivery.
- Guest access with persisted showcase data generated for each guest account.
- Authenticated dashboard with calories in, calories out, net calories, hydration, workouts, active goals, and notifications.
- Workout sessions, exercise entries, exercise library, and workout plans.
- Nutrition entries through manual input, USDA lookup, text-based AI estimation, and photo-based AI estimation.
- Water intake tracking with milliliter and fluid-ounce input.
- Body profile and body-measurement history.
- Goal tracking for calories, net calories, macros, hydration, workout minutes, and workouts per week.
- In-app and email notification records.
- Demo data seeding for repeatable demonstration and QA workflows.
- Unit, regression, coverage, and Playwright browser-level tests.

## Technical Stack

| Layer | Technology |
| --- | --- |
| Backend | Django 4.2, Python 3.10+ |
| Frontend | Django templates, custom CSS |
| Database | SQLite for local development, PostgreSQL for production |
| Runtime | Gunicorn, Nginx, systemd |
| Email | Django SMTP backend, commercial mailbox provider |
| AI features | OpenAI Responses API |
| Nutrition data | USDA FoodData Central API |
| Test automation | Django test runner, Coverage.py, Playwright |
| CI | GitHub Actions |

Primary Python dependencies are listed in `requirements.txt`. Development and QA dependencies are listed in `requirements-dev.txt`.

## System Architecture

TerrierFit is a modular Django monolith. Feature boundaries are represented by Django apps, while routing, settings, authentication views, and shared authentication forms live in the project package.

```text
Browser
  |
  v
Django templates and static assets
  |
  v
fitness_manager/
  settings.py
  urls.py
  auth_views.py
  auth_backends.py
  forms.py
  |
  +-- apps/workouts
  +-- apps/nutrition
  +-- apps/goals
  +-- apps/notifications
  +-- apps/profiles
  |
  v
Django ORM
  |
  v
SQLite or PostgreSQL

Optional external services:
  - SMTP mailbox provider
  - USDA FoodData Central
  - OpenAI Responses API
```

## Repository Layout

```text
Fitness-Manager/
├── apps/
│   ├── goals/                 # Goal models, services, views, templates, tests
│   ├── notifications/         # Notification records and dispatch services
│   ├── nutrition/             # Food, water, USDA, text AI, photo AI workflows
│   ├── profiles/              # User profile and body measurements
│   └── workouts/              # Dashboard, workouts, exercises, plans, browser tests
├── fitness_manager/           # Django project settings, URLs, authentication
├── templates/                 # Shared and registration templates
├── scripts/                   # Demo data and page-probe utilities
├── docs/                      # Supporting documentation and design artifacts
├── .github/workflows/         # GitHub Actions CI definitions
├── manage.py                  # Django management entry point
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Development, coverage, and Playwright dependencies
├── .coveragerc                # Coverage configuration
└── .env.example               # Environment variable template
```

## Configuration

Create a local `.env` file from `.env.example` and set environment-specific values. The `.env` file is intentionally ignored by Git and must not be committed.

Required local development values:

```env
DJANGO_ENV=development
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Production deployments should set:

```env
DJANGO_ENV=production
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<strong-secret>
DJANGO_ALLOWED_HOSTS=<domain>,<server-ip>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<domain>
DJANGO_SECURE_PROXY_SSL_HEADER=1
DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_SECURE_COOKIES=1
```

Email delivery is configured through Django's SMTP backend. The current `.env.example` is aligned with a commercial SMTP mailbox:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=notify@terrierfit.com
DEFAULT_NOTIFICATION_EMAIL=notify@terrierfit.com
EMAIL_HOST=mail.privateemail.com
EMAIL_PORT=465
EMAIL_HOST_USER=notify@terrierfit.com
EMAIL_HOST_PASSWORD=<mailbox-password>
EMAIL_USE_TLS=0
EMAIL_USE_SSL=1
EMAIL_TIMEOUT_SECONDS=10
```

Optional feature keys:

```env
USDA_API_KEY=<usda-api-key>
OPENAI_API_KEY=<openai-api-key>
OPENAI_MODEL=gpt-4o-mini
```

If optional API keys are absent, the application remains usable. USDA lookup and AI-assisted estimation either return no external results or fall back to local behavior where implemented.

## Local Development

Prerequisite: Python 3.10 or newer.

1. Create and activate a virtual environment.

```powershell
python -m venv venv
.\venv\Scripts\Activate
```

2. Install runtime dependencies.

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Create the local environment file.

```powershell
copy .env.example .env
```

4. Apply migrations.

```powershell
python manage.py migrate
```

5. Start the local development server when local browser testing is required.

```powershell
python manage.py runserver
```

Default local URL:

```text
http://127.0.0.1:8000/
```

## Demo Data

The repository includes an idempotent demo-data script for the `demo` account.

```powershell
python scripts/seed_demo.py
```

Default demo credentials:

```text
username: demo
password: demo12345
```

The script clears and recreates demo rows for the demo user so that dashboards, lists, charts, goals, notifications, and edit screens have realistic data.

Guest login uses the same showcase-data generator. Each guest account receives persisted database rows for profile, body metrics, nutrition, hydration, workouts, goals, and notifications, while still remaining isolated from other users.

## Testing and Quality Gates

Install development dependencies before running the complete QA suite:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the Django system check:

```powershell
python manage.py check
```

Run all tests:

```powershell
python manage.py test
```

Run coverage:

```powershell
coverage erase
coverage run manage.py test
coverage report
coverage xml
```

Coverage is configured in `.coveragerc` with branch coverage enabled and a minimum total threshold of 70 percent.

Run Playwright browser-level tests locally:

```powershell
python -m playwright install chromium
python manage.py test apps.workouts.tests_playwright
```

If a system Chrome installation should be used instead of the bundled Playwright browser:

```powershell
$env:PLAYWRIGHT_CHROMIUM_EXECUTABLE="C:\Program Files\Google\Chrome\Application\chrome.exe"
python manage.py test apps.workouts.tests_playwright
```

The Playwright suite covers:

- Login.
- Registration.
- Password reset.
- Mobile layout overflow checks.
- Core authenticated CRUD flows.

GitHub Actions runs the following on push and pull request events:

- Dependency installation.
- `python manage.py check`.
- `coverage run manage.py test --verbosity 2`.
- `coverage report`.
- `coverage xml`.
- Coverage XML upload as a CI artifact.

## External Integrations

### SMTP Email

Password reset and email notifications use Django's SMTP backend. The application expects a working mailbox, valid SMTP password, and compatible TLS or SSL settings. The current production-oriented configuration uses SSL on port 465.

### USDA FoodData Central

The nutrition lookup workflow calls USDA FoodData Central when `USDA_API_KEY` is configured. The service is used to search foods and prefill calories, macros, sodium, and selected micronutrients.

### OpenAI Responses API

AI-assisted features use the OpenAI Responses API when `OPENAI_API_KEY` is configured:

- Meal estimation from text.
- Meal estimation from uploaded food photos.
- Exercise calorie estimation.

Exercise calorie estimation includes a local fallback so core workout logging remains available if the API is unavailable.

## Deployment

The current deployment model is a single-server Django deployment:

- Gunicorn application server.
- Nginx reverse proxy.
- systemd service named `fitness-manager`.
- Static files collected into `staticfiles/`.
- PostgreSQL recommended for production persistence.

Typical production update sequence:

```bash
git pull
python -m pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart fitness-manager
sudo nginx -t
sudo systemctl reload nginx
```

Production verification should include:

```bash
python manage.py check
python manage.py test
```

For live environments, use the local-memory email backend only in tests. Production password reset requires the SMTP backend and valid mailbox credentials.

## Security Considerations

- `.env` is ignored by Git and must remain local to each environment.
- All core application pages require authentication.
- User-owned rows are scoped through `request.user`.
- Guest accounts use unusable passwords and are cleaned up after they become stale.
- Password reset is handled by Django's token-based reset flow.
- Production should enable HTTPS redirect, secure cookies, and proxy SSL headers.
- Uploaded food photos are size-limited and validated before processing.

## Known Limitations

- No dedicated administrative analytics dashboard is included.
- USDA and OpenAI features depend on external API availability and configured keys.
- Some nutrition and hydration recommendations use fixed defaults rather than fully personalized clinical guidance.
- The application is not a medical device and does not provide medical advice.

## License

Internal academic and project use unless a separate license is provided.
