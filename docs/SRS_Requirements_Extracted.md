# SRS Requirements (Extracted)

This file extracts the requirements from `SRS.docx` into an implementation checklist.

## Functional Requirements

### FR-NUT: Nutrition Tracking
- `FR-NUT.1` Record individual food items.
- `FR-NUT.2` Set nutritional information of food records.
- `FR-NUT.3` Edit/delete food records.
- `FR-NUT.4` Associate each food record with a date.
- `FR-NUT.5` No more than 3 steps to record a food item.
- `FR-NUT.6` Display individual item nutrition (calories, macros, micros).
- `FR-NUT.7` Aggregate macros over standard periods.
- `FR-NUT.8` Compare macro intake to recommended values.
- `FR-NUT.9` Aggregate micronutrients over standard periods.
- `FR-NUT.10` Compare micronutrient intake to recommended values.
- `FR-NUT.11` Compute net calories over standard periods.
- `FR-NUT.12` Visually indicate net surplus/deficit.
- `FR-NUT.13` Auto-update net calories after food/workout records.
- `FR-NUT.14` Net calories = food intake - exercise burn.
- `FR-NUT.15` Compute water intake over standard periods.
- `FR-NUT.16` Create water records in ounces or milliliters.
- `FR-NUT.17` Display daily water goal progress.
- `FR-NUT.18` Compute recommended caloric intake using weight/height/sex.
- `FR-NUT.19` Display current daily caloric intake and max recommended value.
- `FR-NUT.20` Generate estimated nutrition values for provided food items.
- `FR-NUT.21` Allow editing generated nutrition before saving.
- `FR-NUT.22` Allow editing nutrition after saving.

### FR-EX: Exercise Tracking
- `FR-EX.1` Record performed exercises.
- `FR-EX.2` Calculate/display calories burned.
- `FR-EX.3` Show consumed vs burned summary.
- `FR-EX.4` Classify exercises by muscle group.
- `FR-EX.5` Show exercise progress metrics over periods.
- `FR-EX.6` Create/customize workout plans.
- `FR-EX.7` Highlight trends in exercise metrics.
- `FR-EX.8` Identify changes in trends.
- `FR-EX.9` Edit/delete prior workouts.

### FR-GOAL: Goal Planning
- `FR-GOAL.1` Create/customize goals.
- `FR-GOAL.2` Configure goal notifications.
- `FR-GOAL.3` Edit goals.
- `FR-GOAL.4` Suggest exercises that fit goals.
- `FR-GOAL.5` Searchable exercise list with descriptions/instructions.

### FR-BM: Body Measurements
- `FR-BM.1` Record weight/body measurements.
- `FR-BM.2` Summaries over standard periods.

### FR-USER: User Management
- `FR-USER.1` Register with unique email + password.
- `FR-USER.2` Authenticate to access private data; terminate sessions.
- `FR-USER.3` Password reset workflow.
- `FR-USER.4` Unauthenticated guest exploration with non-persistent data.
- `FR-USER.5` Per-user data isolation.

### FR-IMG: Food Image Identification
- `FR-IMG.1` Submit photos to identify foods.
- `FR-IMG.2` Compute identified food nutritional values.

## Non-Functional Requirements

### Performance
- `NFR-PERF-001` Authenticated page load within 100ms.
- `NFR-PERF-002` Local actions within 100ms; external integration timeout 20s.
- `NFR-PERF-003` DB query results within 600ms.
- `NFR-PERF-004` Typical page render within 1s.

### Availability & Reliability
- `NFR-REL-001` Show error message on operation failure.
- `NFR-REL-002` Preserve consistency; avoid duplicate saves from refresh/re-submit.
- `NFR-REL-003` Gracefully recover from third-party failures with retry/manual fallback.

### Security
- `NFR-SEC-001` Authenticate before accessing personal data.
- `NFR-SEC-002` Enforce per-user authorization.
- `NFR-SEC-003` Secure one-way password hashing.
- `NFR-SEC-004` Configurable inactivity session timeout.

### Privacy
- `NFR-PRIV-001` Do not display personal data to unauthenticated users.
- `NFR-PRIV-002` For guests, clearly state temporary data behavior.
- `NFR-PRIV-003` Allow deleting logged entries.

### Usability & Accessibility
- `NFR-USE-001` Clear navigation among Nutrition/Exercise/Goals/Profile.
- `NFR-USE-002` Validate input and show actionable messages.
- `NFR-USE-003` Core logging workflows completable within 1 minute.
- `NFR-USE-004` Keyboard navigation for primary actions and readable contrast.

### Maintainability & Extensibility
- `NFR-MAINT-001` Modular separation of UI, business logic, persistence.
- `NFR-MAINT-002` Centralized application error logging.
- `NFR-MAINT-003` Third-party integrations behind service interfaces.

### Compatibility
- `NFR-COMP-001` Support latest Chrome/Firefox/Safari.
- `NFR-COMP-002` Responsive desktop + mobile UI.

## RAIL Performance Requirements
- `RAIL-RESP-001` Interaction feedback < 100ms.
- `RAIL-RESP-002` Common action confirmation < 1s.
- `RAIL-ANIM-001` ~60 FPS smooth animation; degrade gracefully.
- `RAIL-ANIM-002` Avoid animation blocking due to long sync processing.
- `RAIL-IDLE-001` Run non-urgent tasks in idle without disrupting interaction.
- `RAIL-IDLE-002` Defer heavy tasks server-side with progress indicators.
- `RAIL-LOAD-001` Initial app shell load within 2s.
- `RAIL-LOAD-002` Summary pages (incl charts) within 2s for typical volume.
- `RAIL-LOAD-003` Show visible loading state if render > 1s.

## Detailed UI/Module Requirements (Condensed)
- Authentication pages: login/register/password-reset/guest.
- Dashboard: calories in/out/net, water progress, goal progress, recent activity, trend widgets.
- Nutrition module: add/edit/delete, image upload, generated-value review, historical list, period summaries.
- Exercise module: logging, searchable exercise library, history, performance metrics/trends, workout plans.
- Body metrics module: log weight/measurements + history/trends.
- Goal module: create/edit/delete goals + progress + reminders + recommendations.
- Notifications: in-app message display (banner/toast/dashboard alerts).
- System dependencies: Django + SQL DB + nutrition APIs + AI image API.

