# TerrierFit (Fitness Manager)

Midterm Presentation - Version 1

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

- Backend: Django 4.x
- Database: SQLite (local) / configurable for production
- Frontend: Django templates + custom CSS
- AI integration: OpenAI Responses API (photo + text nutrition estimate)
- External data: USDA FoodData Central API
- Deployment: Gunicorn + Nginx + systemd (EC2)

## Repository Structure

```text
apps/
  workouts/
  nutrition/
  goals/
  notifications/
  profiles/
fitness_manager/
templates/
features/config/
```

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

- `USDA_API_KEY` for USDA food search
- `OPENAI_API_KEY` for AI estimate from text/photo
- `OPENAI_MODEL` (example: `gpt-4.1-mini`)

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
