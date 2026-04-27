# TerrierFit (Fitness Manager)

TerrierFit is a Django-based fitness tracking app focused on daily consistency: workouts, nutrition, hydration, goals, and progress visibility in one place.

## Project Highlights

- Unified dashboard for calories in/out, net calories, hydration progress, active goals, workouts, and notifications
- Workout logging with exercise-level details and calorie burn tracking
- Nutrition logging with multiple input modes:
  - Manual entry
  - USDA food search (FoodData Central)
  - AI estimate from meal description
  - AI estimate from meal photo
- Water intake tracking with period summaries
- Body metrics tracking (weight and measurements)
- Goal tracking with reminders
- User authentication and per-user data isolation across all features

## Demo Flow (Recommended for Presentation)

1. Open Dashboard to show daily snapshot
2. Go to Nutrition -> Add Food -> Quick Add Options
3. Show USDA lookup and AI estimate entry paths
4. Show Nutrition Summary (day/week/month)
5. Show Workouts and Body Metrics trends
6. Show Goals and Notifications

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 4.2 (Python 3.10+) |
| Frontend | Django Templates + custom CSS (server-side rendering) |
| Database | SQLite (local dev) / PostgreSQL 16 (production) |
| AI Integration | OpenAI Responses API (`gpt-4o-mini` / configurable) |
| External Data | USDA FoodData Central API |
| Email | Commercial SMTP (password reset + notifications) |
| Deployment | Gunicorn + Nginx + systemd (EC2) or Docker Compose |

Key Python dependencies: `Django`, `Pillow`, `requests`, `psycopg2-binary`, `gunicorn`.

## Architecture Overview

TerrierFit is a **monolithic Django application** composed of five feature apps plus a project-level package for settings and authentication. All pages are rendered server-side; there is no separate SPA layer or JSON REST API.

```text
                    ┌─────────────────────────────────────────┐
                    │          Django Templates (HTML)        │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────────┐
                    │        fitness_manager/ (project)        │
                    │  settings · urls · auth_views · email    │
                    └──────────────────┬──────────────────────┘
                                       │
          ┌──────────┬─────────────────┼─────────────────┬──────────────┐
          │          │                 │                 │              │
   ┌──────┴────┐ ┌───┴────┐ ┌─────────┴──────┐ ┌─────────┴──────┐ ┌─────┴──────┐
   │ workouts  │ │ goals  │ │   nutrition    │ │ notifications  │ │  profiles  │
   │           │ │        │ │                │ │                │ │            │
   │ Workout   │ │ Goal   │ │ FoodEntry      │ │ Notification   │ │ UserProfile│
   │ Exercise  │ │        │ │ WaterEntry     │ │                │ │ BodyMeasur.│
   │ Plan      │ │        │ │ FoodPhoto      │ │                │ │            │
   │ Library   │ │        │ │                │ │                │ │            │
   └─────┬─────┘ └───┬────┘ └───────┬────────┘ └───────┬────────┘ └─────┬──────┘
         │           │              │                  │                │
         └───────────┴──────────────┴──────────────────┴────────────────┘
                                       │
                    ┌──────────────────┴──────────────────────┐
                    │            Django ORM (SQL)              │
                    └──────────────────┬──────────────────────┘
                                       │
                         ┌─────────────┴──────────────┐
                         │ SQLite (dev) / PostgreSQL  │
                         └────────────────────────────┘

External services:  USDA FoodData · OpenAI Responses API · SMTP
```

## Repository Structure

```text
Fitness-Manager/
├── fitness_manager/           # Django project settings & authentication
│   ├── settings.py            # Global configuration
│   ├── urls.py                # Root URL routing
│   ├── auth_views.py          # Signup, guest login, logout
│   ├── auth_backends.py       # Email-or-username authentication backend
│   └── forms.py               # Auth forms (signup, login)
│
├── apps/                      # Feature apps
│   ├── workouts/              # Workouts, exercises, plans, library, dashboard
│   ├── nutrition/             # Food, water, photo, USDA lookup, AI estimate
│   ├── goals/                 # Goal setting and progress calculation
│   ├── notifications/         # In-app and email notifications
│   └── profiles/              # User profile and body measurements
│
├── templates/                 # HTML templates (registration/, base.html)
├── features/config/           # Dockerfile, docker-compose.yml, entrypoint.sh
├── .deploy/                   # Deployment scripts and artifacts
├── docs/                      # Project documentation
├── manage.py                  # Django management entry point
├── requirements.txt           # Python dependencies
└── .env.example               # Example environment variables
```

## Data Models

All user data is isolated via `ForeignKey(user)` and queried through `request.user`. Six core domains:

### Profiles
- **UserProfile** — one-to-one with `User`; stores sex, age, height, weight, activity level, and daily water goal. Exposes `activity_multiplier()` and `estimated_daily_calories()` (Mifflin-St Jeor BMR).
- **BodyMeasurement** — weight, waist, chest, hip, body fat %, dated entries.

### Workouts
- **Workout** — a training session (name, date, notes).
- **ExerciseEntry** — individual exercise logged against a workout (name, category, muscle group, duration, calories burned, `auto_classified` flag).
- **ExerciseLibrary** — global reference catalog (name, category, muscle group, instructions).
- **WorkoutPlan** — user-defined plan with focus, sessions per week, details.

### Nutrition
- **FoodEntry** — name, brand, quantity, macros (`calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`, `sugar_g`, `sodium_mg`), micronutrients (`JSONField`), source (`manual | usda | image`), timestamp.
- **WaterEntry** — amount in ml, timestamp.
- **FoodPhoto** — uploaded image, processing status, recognized name, AI payload (`JSONField`), error message.

### Goals
- **Goal** — name, type, target value, unit, start/end dates, `active`, notification preferences, `last_notified_at`.
- Supported goal types: `calories`, `net_calories`, `protein`, `carbs`, `fat`, `water`, `workout_minutes`, `workouts_per_week`.

### Notifications
- **Notification** — channel (`inapp | email | push`), status (`pending | sent | failed`), message, optional `goal` link.

## Application Routes

All core routes require authentication (`@login_required`).

### Authentication
| Route | Method | View |
|-------|--------|------|
| `/login/` | GET/POST | Email-or-username login |
| `/signup/` | GET/POST | Create user and profile |
| `/guest/` | POST | Temporary guest session (24h cleanup) |
| `/logout/` | POST | Logout (deletes guest accounts) |
| `/password-reset/` | GET/POST | Request reset email (via SES) |
| `/password-reset/done/` | GET | Reset email sent confirmation |
| `/reset/<uidb64>/<token>/` | GET/POST | Set new password |
| `/reset/done/` | GET | Reset complete |

### Dashboard
| Route | View |
|-------|------|
| `/` | Daily dashboard: calories in/out, net calories, water, recent workouts, top goals, notifications, recommended daily calories |

### Workouts (`apps/workouts/urls.py`)
| Route | Method | View |
|-------|--------|------|
| `/workouts/` | GET | Workout list |
| `/workouts/add/` | GET/POST | Add workout |
| `/workouts/<id>/` | GET | Workout detail |
| `/workouts/<id>/edit/` | GET/POST | Edit workout |
| `/workouts/<id>/delete/` | POST | Delete workout |
| `/workouts/<id>/exercise/add/` | GET/POST | Add exercise (with AI calorie estimate) |
| `/workouts/<id>/exercise/<ex_id>/edit/` | GET/POST | Edit exercise |
| `/workouts/<id>/exercise/<ex_id>/delete/` | POST | Delete exercise |
| `/exercise-library/` | GET | Browse exercise library |
| `/plans/` | GET | Workout plan list |
| `/plans/add/` | GET/POST | Create plan |
| `/plans/<id>/edit/` | GET/POST | Edit plan |
| `/plans/<id>/delete/` | POST | Delete plan |

### Nutrition (`apps/nutrition/urls.py`)
| Route | Method | View |
|-------|--------|------|
| `/nutrition/` | GET | Food list |
| `/nutrition/add/` | GET/POST | Add food (supports prefill params) |
| `/nutrition/<id>/edit/` | GET/POST | Edit food |
| `/nutrition/<id>/delete/` | POST | Delete food |
| `/nutrition/lookup/` | GET | USDA food search |
| `/nutrition/summary/` | GET | Macro/micro summary (day/week/month) |
| `/nutrition/photo/` | GET/POST | AI photo recognition |
| `/nutrition/estimate/` | GET/POST | AI text-based estimate |
| `/nutrition/water/` | GET | Water log list |
| `/nutrition/water/add/` | GET/POST | Add water entry (ml or oz) |
| `/nutrition/water/<id>/edit/` | GET/POST | Edit water entry |
| `/nutrition/water/<id>/delete/` | POST | Delete water entry |

### Goals (`apps/goals/urls.py`)
| Route | Method | View |
|-------|--------|------|
| `/goals/` | GET | Goal list with live progress |
| `/goals/add/` | GET/POST | Create goal |
| `/goals/<id>/edit/` | GET/POST | Edit goal |
| `/goals/<id>/delete/` | POST | Delete goal |

### Profiles (`apps/profiles/urls.py`)
| Route | Method | View |
|-------|--------|------|
| `/profile/` | GET/POST | Edit profile |
| `/profile/body-metrics/` | GET | Body metrics list |
| `/profile/body-metrics/add/` | GET/POST | Add body metric |
| `/profile/body-metrics/<id>/edit/` | GET/POST | Edit body metric |
| `/profile/body-metrics/<id>/delete/` | POST | Delete body metric |

### Notifications (`apps/notifications/urls.py`)
| Route | Method | View |
|-------|--------|------|
| `/notifications/` | GET | Notification list |

### Admin
| Route | View |
|-------|------|
| `/admin/` | Django admin panel |

## External Service Integrations

### USDA FoodData Central (`apps/nutrition/services.py`)
- Endpoint: `https://api.nal.usda.gov/fdc/v1/foods/search`
- Used by `/nutrition/lookup/` to search foods and prefill nutrition.
- Parses calories, macros, sodium, and selected micronutrients (iron, calcium, vitamin C, potassium).
- Retry: 2 attempts with 0.4s backoff; degrades gracefully if `USDA_API_KEY` is missing.

### OpenAI Responses API (`apps/nutrition/vision.py`, `apps/workouts/ai.py`)
Three AI features, all consuming the OpenAI Responses API (`temperature=0.1–0.2`, JSON-only output):
1. **Food photo recognition** — image is re-encoded to JPEG base64 (max 1024×1024) and sent for nutrition extraction.
2. **Text-based meal estimate** — meal description converted into macros/micros JSON.
3. **Exercise calorie estimate** — given exercise name, duration, category, muscle group, and weight, returns `calories_burned`. Falls back to category-based per-minute rates if the API is unavailable.

### Email Delivery
- Email is sent through Django's built-in SMTP backend.
- Namecheap Private Email uses `mail.privateemail.com` with port `465` and SSL in the current deployment.
- `DEFAULT_FROM_EMAIL` and `DEFAULT_NOTIFICATION_EMAIL` are both expected to use `notify@terrierfit.com`.

## Authentication Flow

- **Custom backend** (`EmailOrUsernameModelBackend`) allows login with either email or username (case-insensitive), then falls back to the default `ModelBackend`.
- **Signup** supports email-first registration, auto-generates a unique username when omitted, creates a `User` and linked `UserProfile` in one transaction, then auto-logs in.
- **Guest login** (POST only) creates a random `guest_<hex>` user with an unusable password; stale guest accounts older than 24h are cleaned up on each guest login.
- **Sessions** default to a 2-hour idle timeout (`DJANGO_SESSION_TIMEOUT_SECONDS`) and refresh on every request.
- **Password reset** uses a guarded Django password reset view with SMTP-backed email delivery.

## Core Business Logic

| Service | Location | Behavior |
|---------|----------|----------|
| BMR estimate | `apps/profiles/models.py` | Mifflin-St Jeor formula × activity multiplier (1.2–1.9) |
| Goal progress | `apps/goals/services.py::calculate_goal_progress` | Dispatches goal type to an aggregate query over food/exercise/water entries |
| Exercise recommendation | `apps/goals/services.py::recommend_exercises_for_goal` | Maps goal type to `ExerciseLibrary` categories |
| Exercise classification | `apps/workouts/utils.py::classify_exercise` | Keyword-based category/muscle mapping |
| Calorie estimate fallback | `apps/workouts/utils.py::estimate_calories` | Per-minute rate by category when AI unavailable |
| Notification dispatch | `apps/notifications/services.py::send_notification` | Creates record, dispatches per channel, updates status |

## Local Setup

Prerequisite: Python 3.10+

1. Create virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Configure environment

```powershell
copy .env.example .env
```

Minimum local values in `.env`:

```env
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

4. Migrate and run

```powershell
python manage.py migrate
python manage.py runserver
```

App URL: `http://127.0.0.1:8000/`

## Optional API Integrations

Set these in `.env`:

- `USDA_API_KEY` — USDA food search
- `OPENAI_API_KEY` — AI estimates (photo, text, exercise calories)
- `OPENAI_MODEL` — e.g. `gpt-4.1-mini`, `gpt-4o-mini`
- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL` — SMTP email delivery

If keys are missing, those features remain visible but may return no results / fallback behavior.

## Testing

Run all tests:

```powershell
python manage.py test
```

Run nutrition tests only:

```powershell
python manage.py test apps.nutrition
```

Static checks:

```powershell
python manage.py check
```

## Production Deployment (Current Pattern)

Target runtime:

- Gunicorn on `127.0.0.1:8010`
- Nginx reverse proxy
- systemd service: `fitness-manager`
- Static files served from `staticfiles/`

Typical update steps on server:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart fitness-manager
sudo nginx -t && sudo systemctl reload nginx
```

## Security and Data Scope

- Auth required for all core user pages
- Data access is scoped by `request.user` in views and queries
- No cross-user read/write should be possible under normal flows

## Known Limitations (V1)

- No dedicated admin analytics dashboard yet
- USDA/OpenAI features depend on API key configuration
- Some summary targets are currently fixed defaults and not fully personalized

## Roadmap (Post-Midterm)

- Improve personalization of nutrition and workout recommendations
- Add richer charts for trend analysis
- Add better onboarding and inline guidance
- Expand test coverage for UI workflows

## License

Internal academic/project use unless otherwise specified.
