# Fitness Manager

Fitness tracking app (workouts, nutrition, goals, notifications) with:
- Django auth (login/signup/logout)
- Per-user data isolation (all models are user-owned and views are scoped to `request.user`)
- Food photo recognition (OpenAI) + nutrition lookup (USDA)

## Quickstart (Local Dev)
Prereqs: Python 3.10+

1. Create and activate a venv
   - Windows (PowerShell):
     - `python -m venv venv`
     - `.\venv\Scripts\Activate`
   - Linux/macOS:
     - `python3 -m venv venv`
     - `source venv/bin/activate`

2. Install deps
   - `pip install -r requirements.txt`

3. Create a local `.env` (optional but recommended)
   - Copy `.env.example` -> `.env`
   - Set at least:
     - `DJANGO_DEBUG=1`
     - `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`

4. Migrate + run
   - `python manage.py migrate`
   - `python manage.py runserver`

Open `http://127.0.0.1:8000/`.

Auth:
- Signup: `/signup/`
- Login: `/login/`
- Admin: `/admin/` (create superuser via `python manage.py createsuperuser`)

## Integrations (Optional)
Set in `.env` (do not commit `.env`):
- `USDA_API_KEY`: enables USDA FoodData Central lookup
- `OPENAI_API_KEY`: enables food photo recognition
- `OPENAI_MODEL`: model for recognition (e.g. `gpt-4.1-mini`)

## Notifications
Goal reminders command:
- `python manage.py send_goal_notifications`

## Production Notes
This repo supports environment-based config via `.env` (loaded by `python-dotenv`).

Minimum required env for production:
- `DJANGO_ENV=production`
- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY=...` (required)
- `DJANGO_ALLOWED_HOSTS=your.domain,www.your.domain`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://your.domain,https://www.your.domain`

Static/media:
- `collectstatic` outputs to `staticfiles/` (served by Nginx in a typical setup)
- user uploads go to `media/`

## Example Deployment (Nginx + systemd + Gunicorn)
High-level:
1. Install system deps: `python3`, `python3-pip`, `nginx`
2. Create venv and `pip install -r requirements.txt`
3. Configure `/home/ec2-user/fitness-manager/.env`
4. Run:
   - `python manage.py migrate --noinput`
   - `python manage.py collectstatic --noinput`
5. Run Gunicorn via systemd (bind to `127.0.0.1:8010`), and reverse-proxy via Nginx.
6. Use Certbot to enable HTTPS.
