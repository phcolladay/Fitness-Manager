# SRS Implementation Status (Code Traceability)

This file maps extracted SRS requirements to implementation points in code.

## FR-NUT Nutrition Tracking

- `FR-NUT.1`/`FR-NUT.2`/`FR-NUT.4`: food record creation with nutrition + timestamp
  - `apps/nutrition/models.py`
  - `apps/nutrition/forms.py`
  - `apps/nutrition/views.py` (`food_add`)
- `FR-NUT.3`/`FR-NUT.22`: edit/delete saved food records
  - `apps/nutrition/views.py` (`food_edit`, `food_delete`)
  - `apps/nutrition/urls.py`
  - `apps/nutrition/templates/nutrition/food_list.html`
- `FR-NUT.5`: fast entry flow (manual + API prefill + photo prefill)
  - `apps/nutrition/templates/nutrition/food_list.html`
  - `apps/nutrition/views.py` (`_prefill_add_url`)
- `FR-NUT.6`: per-item nutrition display
  - `apps/nutrition/templates/nutrition/food_list.html`
- `FR-NUT.7`/`FR-NUT.8`/`FR-NUT.9`/`FR-NUT.10`/`FR-NUT.11`/`FR-NUT.12`/`FR-NUT.14`:
  period summaries, macro/micro comparison, net surplus/deficit
  - `apps/nutrition/views.py` (`food_summary`)
  - `apps/nutrition/templates/nutrition/food_summary.html`
- `FR-NUT.13`: auto-update net values after records (computed from current DB state)
  - `apps/nutrition/views.py` (`food_summary`)
  - `apps/workouts/views.py` (`home`)
- `FR-NUT.15`/`FR-NUT.16`/`FR-NUT.17`: water totals + ml/oz entry + progress
  - `apps/nutrition/forms.py` (`WaterEntryForm`)
  - `apps/nutrition/views.py` (`water_list`, `water_add`, `water_edit`, `water_delete`)
  - `apps/nutrition/templates/nutrition/water_list.html`
- `FR-NUT.18`/`FR-NUT.19`: recommended calories and daily intake vs max
  - `apps/profiles/models.py` (`estimated_daily_calories`)
  - `apps/workouts/views.py` (`home`)
  - `apps/workouts/templates/workouts/home.html`
- `FR-NUT.20`/`FR-NUT.21`: generated estimates editable before save
  - `apps/nutrition/views.py` (`food_estimate`, `food_photo_upload`)
  - `apps/nutrition/vision.py`
  - `apps/nutrition/templates/nutrition/food_estimate.html`

## FR-EX Exercise Tracking

- `FR-EX.1`/`FR-EX.2`/`FR-EX.4`: exercise logging, calories burned, classification fields
  - `apps/workouts/models.py`
  - `apps/workouts/views.py` (`exercise_add`)
  - `apps/workouts/utils.py`
- `FR-EX.3`: consumed vs burned summary
  - `apps/workouts/views.py` (`home`)
  - `apps/workouts/templates/workouts/home.html`
- `FR-EX.5`/`FR-EX.7`/`FR-EX.8`: period metrics + trend delta
  - `apps/workouts/views.py` (`workout_list`, `_workout_period`)
  - `apps/workouts/templates/workouts/workout_list.html`
- `FR-EX.6`: workout plans
  - `apps/workouts/models.py` (`WorkoutPlan`)
  - `apps/workouts/views.py` (`plan_*`)
  - `apps/workouts/templates/workouts/plan_list.html`
- `FR-EX.9`: edit/delete workouts and exercises
  - `apps/workouts/views.py` (`workout_edit/delete`, `exercise_edit/delete`)

## FR-GOAL Goal Planning

- `FR-GOAL.1`/`FR-GOAL.3`: create/edit goals
  - `apps/goals/views.py`
  - `apps/goals/forms.py`
- `FR-GOAL.2`: notification toggles in goal form + reminder command
  - `apps/goals/models.py`
  - `apps/notifications/management/commands/send_goal_notifications.py`
- `FR-GOAL.4`: exercise recommendations by goal type
  - `apps/goals/services.py` (`recommend_exercises_for_goal`)
  - `apps/goals/templates/goals/goal_list.html`
- `FR-GOAL.5`: searchable exercise library with description/instructions
  - `apps/workouts/models.py` (`ExerciseLibrary`)
  - `apps/workouts/views.py` (`exercise_library`)
  - `apps/workouts/templates/workouts/exercise_library.html`

## FR-BM Body Measurements

- `FR-BM.1`: record body metrics
  - `apps/profiles/models.py` (`BodyMeasurement`)
  - `apps/profiles/views.py` (`body_metric_*`)
- `FR-BM.2`: daily/weekly/monthly summaries and trend
  - `apps/profiles/views.py` (`body_metrics_list`)
  - `apps/profiles/templates/profiles/body_metrics_list.html`

## FR-USER User Management

- `FR-USER.1`: registration with unique email + password
  - `fitness_manager/forms.py` (`SignupForm.clean_email`)
  - `fitness_manager/auth_views.py` (`signup`)
- `FR-USER.2`: authentication + logout + session timeout
  - `fitness_manager/urls.py` (login/logout routes)
  - `fitness_manager/settings.py` (`SESSION_COOKIE_AGE`, backends)
  - `templates/base.html` (POST logout)
- `FR-USER.3`: password reset flow
  - `fitness_manager/urls.py` (`password-reset/*`)
  - `templates/registration/password_reset_*.html`
- `FR-USER.4`: guest mode with temporary semantics
  - `fitness_manager/auth_views.py` (`guest_login`, `logout_view`, stale cleanup)
  - `templates/registration/login.html`
- `FR-USER.5`: per-user ownership + scoped access
  - all domain models include `user` foreign key
  - all business views filtered by `request.user`

## FR-IMG Food Image Identification

- `FR-IMG.1`/`FR-IMG.2`: upload photo and estimate nutrition
  - `apps/nutrition/forms.py` (`FoodPhotoForm` validations)
  - `apps/nutrition/views.py` (`food_photo_upload`)
  - `apps/nutrition/vision.py`

## NFR Coverage

- Reliability and controlled errors:
  - `apps/nutrition/services.py` (USDA failures handled + retry)
  - `apps/nutrition/vision.py` (OpenAI responses retry + strict JSON parsing)
  - `apps/nutrition/views.py` (OpenAI/USDA errors shown as user-safe messages)
  - PRG pattern on writes (redirect after POST in create/update/delete views)
- Security/privacy:
  - login-required on business endpoints
  - strict per-user filtering
  - password hashing via Django auth
  - session timeout configurable by env
- Maintainability:
  - integrations isolated in `apps/nutrition/services.py` and `apps/nutrition/vision.py`
  - centralized logging config in `fitness_manager/settings.py`
- Compatibility/responsive:
  - responsive navigation/layout in `apps/workouts/static/terrierfit.css`
  - delayed loading indicators for long-running forms (`templates/base.html`, nutrition templates)

## Notes

- Performance thresholds in SRS (e.g., exact millisecond targets) depend on deployment environment/load and are not hardcoded in app logic.
- Exercise library is seeded by migration:
  - `apps/workouts/migrations/0006_seed_exercise_library.py`
