# Fitness Manager

Fitness tracking app (workouts, nutrition, goals, notifications) with:
- Django auth (login/signup/logout)
- Per-user data isolation (all models are user-owned and views are scoped to `request.user`)
- Food photo recognition (OpenAI) + nutrition lookup (USDA)

Production instance (example):
- Domain: `https://terrierfit.com/`
- App server (Gunicorn): `127.0.0.1:8010` behind Nginx

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
- `OPENAI_API_KEY`: enables food photo recognition (OpenAI Responses API)
- `OPENAI_MODEL`: model for recognition (e.g. `gpt-4.1-mini`)

OpenAI notes:
- This project uses the OpenAI Responses API endpoint `POST /v1/responses`.
- Structured JSON output is requested via `text.format: { type: "json_object" }` (older `response_format` will 400).

## Notifications
Goal reminders command:
- `python manage.py send_goal_notifications`

## Production Notes
This repo supports environment-based config via `.env` (loaded by `python-dotenv`).

### Environment Variables
Common variables (matches `.env.example`):
- `DJANGO_ENV`: `development` or `production` (used to toggle sensible defaults)
- `DJANGO_DEBUG`: `1` enables debug, `0` disables (must be `0` in production)
- `DJANGO_SECRET_KEY`: Django secret key (required in production; never commit)
- `DJANGO_ALLOWED_HOSTS`: comma-separated hosts (e.g. `terrierfit.com,www.terrierfit.com,127.0.0.1,localhost`)
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated origins including scheme (e.g. `https://terrierfit.com,https://www.terrierfit.com`)
- `DJANGO_LOG_LEVEL`: `DEBUG`/`INFO`/`WARNING`/`ERROR`
- `FOOD_PHOTO_MAX_UPLOAD_SIZE`: max upload bytes for food photo (default 5MB)
- `DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE`: Django request body limit in bytes
- `DJANGO_SECURE_PROXY_SSL_HEADER`: `1` if running behind a TLS-terminating proxy (Nginx/ALB) setting `X-Forwarded-Proto`
- `DJANGO_SECURE_SSL_REDIRECT`: `1` to redirect HTTP->HTTPS at Django layer (often handled by Nginx instead)
- `DJANGO_SECURE_COOKIES`: `1` to set secure cookies (recommended for HTTPS)
- `USDA_API_KEY`: USDA FoodData Central key (optional)
- `OPENAI_API_KEY`: OpenAI key for photo recognition (optional, required for recognition to work)
- `OPENAI_MODEL`: model name for photo recognition (e.g. `gpt-4.1-mini`)
- `DEFAULT_FROM_EMAIL`: email sender (from)
- `DEFAULT_NOTIFICATION_EMAIL`: email recipient for notifications (to)

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

### Domain + Nginx (same EIP as other site)
If you already have another domain on the same Elastic IP (for example `reskin.ink`), you bind this app by adding another server block using `server_name terrierfit.com www.terrierfit.com` and proxying to a different upstream port (here: `8010`).

Minimal Nginx shape (conceptual):
```nginx
server {
  listen 443 ssl;
  server_name terrierfit.com www.terrierfit.com;

  location /static/ { alias /home/ec2-user/fitness-manager/staticfiles/; }
  location /media/  { alias /home/ec2-user/fitness-manager/media/; }

  location / {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass http://127.0.0.1:8010;
  }
}
```

After code updates on the server:
1. `python manage.py migrate --noinput`
2. `python manage.py collectstatic --noinput`
3. `sudo systemctl restart fitness-manager`
4. `sudo nginx -t && sudo systemctl reload nginx`

### HTTPS (Certbot)
One-time (example):
- `sudo certbot --nginx -d terrierfit.com -d www.terrierfit.com`

Renewal (typical):
- `sudo certbot renew --dry-run`
