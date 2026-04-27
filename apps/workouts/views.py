from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.goals.models import Goal
from apps.nutrition.models import FoodEntry, WaterEntry
from apps.notifications.models import Notification
from apps.profiles.models import UserProfile

from .forms import ExerciseEntryForm, WorkoutForm, WorkoutPlanForm
from .models import ExerciseEntry, ExerciseLibrary, Workout, WorkoutPlan
from .ai import estimate_exercise_calories_ai
from .utils import classify_exercise, estimate_calories


def _dashboard_charts(user, today, *, water_goal_ml: int, recommended_calories):
    """Build 7-day SVG bar-chart data for the home dashboard cards.

    Returns a dict ready to merge into the template context. All bar
    coordinates are pre-computed so the template only iterates and renders.
    """
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    start, end = days[0], days[-1]

    food_by_day = {
        row["consumed_at__date"]: float(row["total"] or 0)
        for row in FoodEntry.objects.filter(
            user=user, consumed_at__date__range=(start, end)
        ).values("consumed_at__date").annotate(total=Sum("calories"))
    }
    burn_by_day = {
        row["workout__performed_on"]: float(row["total"] or 0)
        for row in ExerciseEntry.objects.filter(
            user=user, workout__performed_on__range=(start, end)
        ).values("workout__performed_on").annotate(total=Sum("calories_burned"))
    }
    water_by_day = {
        row["consumed_at__date"]: int(row["total"] or 0)
        for row in WaterEntry.objects.filter(
            user=user, consumed_at__date__range=(start, end)
        ).values("consumed_at__date").annotate(total=Sum("amount_ml"))
    }
    macros_by_day = {
        row["consumed_at__date"]: row
        for row in FoodEntry.objects.filter(
            user=user, consumed_at__date__range=(start, end)
        ).values("consumed_at__date").annotate(
            protein=Sum("protein_g"), carbs=Sum("carbs_g"), fat=Sum("fat_g"),
        )
    }

    W = 700
    PAD_L, PAD_R, PAD_T, PAD_B = 16, 16, 14, 28

    def _band_geom(height):
        plot_w = W - PAD_L - PAD_R
        plot_h = height - PAD_T - PAD_B
        band = plot_w / len(days)
        bar = max(20.0, band * 0.55)
        return plot_h, band, bar

    # ---------- Calories chart (in vs. out, side-by-side bars) ----------
    H_CAL = 200
    plot_h, band_w, bar_w = _band_geom(H_CAL)
    cal_in = [food_by_day.get(d, 0.0) for d in days]
    cal_out = [burn_by_day.get(d, 0.0) for d in days]
    cal_max = max(cal_in + cal_out + [float(recommended_calories or 0), 1.0]) * 1.1
    half = bar_w / 2 - 1
    cal_bars = []
    for i, d in enumerate(days):
        in_v, out_v = cal_in[i], cal_out[i]
        in_h = (in_v / cal_max) * plot_h
        out_h = (out_v / cal_max) * plot_h
        cx = PAD_L + i * band_w + band_w / 2
        baseline = PAD_T + plot_h
        cal_bars.append({
            "in_x": round(cx - half - 1, 1),
            "in_y": round(baseline - in_h, 1),
            "in_w": round(half, 1),
            "in_h": round(in_h, 1),
            "in_v": int(in_v),
            "out_x": round(cx + 1, 1),
            "out_y": round(baseline - out_h, 1),
            "out_w": round(half, 1),
            "out_h": round(out_h, 1),
            "out_v": int(out_v),
            "label": d.strftime("%a"),
            "label_x": round(cx, 1),
            "is_today": d == today,
        })
    calories_chart = {
        "bars": cal_bars,
        "width": W,
        "height": H_CAL,
        "x0": PAD_L,
        "x1": W - PAD_R,
        "baseline_y": PAD_T + plot_h,
        "label_y": H_CAL - 8,
        "rec_y": (round(PAD_T + plot_h - (float(recommended_calories) / cal_max) * plot_h, 1)
                  if recommended_calories else None),
        "max": int(cal_max),
    }

    # ---------- Hydration chart (single bars + goal line) ----------
    H_WTR = 200
    plot_h, band_w, bar_w = _band_geom(H_WTR)
    wtr_vals = [water_by_day.get(d, 0) for d in days]
    wtr_max = max(wtr_vals + [water_goal_ml or 1]) * 1.1
    wtr_bars = []
    for i, d in enumerate(days):
        v = wtr_vals[i]
        h = (v / wtr_max) * plot_h
        cx = PAD_L + i * band_w + band_w / 2
        baseline = PAD_T + plot_h
        wtr_bars.append({
            "x": round(cx - bar_w / 2, 1),
            "y": round(baseline - h, 1),
            "w": round(bar_w, 1),
            "h": round(h, 1),
            "v": v,
            "label": d.strftime("%a"),
            "label_x": round(cx, 1),
            "is_today": d == today,
        })
    water_chart = {
        "bars": wtr_bars,
        "width": W,
        "height": H_WTR,
        "x0": PAD_L,
        "x1": W - PAD_R,
        "baseline_y": PAD_T + plot_h,
        "label_y": H_WTR - 8,
        "goal_y": (round(PAD_T + plot_h - (water_goal_ml / wtr_max) * plot_h, 1)
                   if water_goal_ml else None),
        "max": int(wtr_max),
    }

    # ---------- Macros chart (stacked P/C/F) ----------
    H_MAC = 240
    PAD_T_MAC = PAD_T + 24  # extra room for legend
    plot_h = H_MAC - PAD_T_MAC - PAD_B
    plot_w = W - PAD_L - PAD_R
    band_w = plot_w / len(days)
    bar_w = max(24.0, band_w * 0.6)
    mac_rows = []
    for d in days:
        row = macros_by_day.get(d, {})
        mac_rows.append({
            "p": float(row.get("protein", 0) or 0),
            "c": float(row.get("carbs", 0) or 0),
            "f": float(row.get("fat", 0) or 0),
            "label": d.strftime("%a"),
            "is_today": d == today,
        })
    mac_max = max([r["p"] + r["c"] + r["f"] for r in mac_rows] + [1.0]) * 1.1
    mac_bars = []
    for i, m in enumerate(mac_rows):
        cx = PAD_L + i * band_w + band_w / 2
        x = cx - bar_w / 2
        baseline = PAD_T_MAC + plot_h
        p_h = (m["p"] / mac_max) * plot_h
        c_h = (m["c"] / mac_max) * plot_h
        f_h = (m["f"] / mac_max) * plot_h
        mac_bars.append({
            "x": round(x, 1),
            "w": round(bar_w, 1),
            "p_y": round(baseline - p_h, 1),
            "p_h": round(p_h, 1),
            "p_v": int(m["p"]),
            "c_y": round(baseline - p_h - c_h, 1),
            "c_h": round(c_h, 1),
            "c_v": int(m["c"]),
            "f_y": round(baseline - p_h - c_h - f_h, 1),
            "f_h": round(f_h, 1),
            "f_v": int(m["f"]),
            "total_v": int(m["p"] + m["c"] + m["f"]),
            "label": m["label"],
            "label_x": round(cx, 1),
            "is_today": m["is_today"],
        })
    macros_chart = {
        "bars": mac_bars,
        "width": W,
        "height": H_MAC,
        "x0": PAD_L,
        "x1": W - PAD_R,
        "baseline_y": PAD_T_MAC + plot_h,
        "label_y": H_MAC - 8,
        "legend_y": PAD_T + 4,
        "max": int(mac_max),
    }

    return {
        "calories_chart": calories_chart,
        "water_chart": water_chart,
        "macros_chart": macros_chart,
    }


def _workout_period(period: str):
    today = timezone.localdate()
    if period == "month":
        days = 30
    elif period == "day":
        days = 1
    else:
        period = "week"
        days = 7
    start = today - timedelta(days=days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return period, start, today, prev_start, prev_end


def _populate_classification(exercise: ExerciseEntry) -> None:
    if not exercise.category or not exercise.muscle_group:
        exercise.category, exercise.muscle_group = classify_exercise(exercise.exercise_name)
        exercise.auto_classified = True


def _estimate_calories_with_ai_or_fallback(*, exercise: ExerciseEntry, user) -> bool:
    if exercise.calories_burned or not exercise.duration_minutes:
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    weight = float(profile.weight_kg) if profile.weight_kg is not None else None
    ai_estimate = estimate_exercise_calories_ai(
        exercise_name=exercise.exercise_name,
        duration_minutes=int(exercise.duration_minutes),
        category=exercise.category or "",
        muscle_group=exercise.muscle_group or "",
        weight_kg=weight,
    )
    if ai_estimate is not None:
        exercise.calories_burned = ai_estimate
        return True
    exercise.calories_burned = estimate_calories(exercise.category, exercise.duration_minutes)
    return False


def _exercise_prefill_query(data: dict) -> str:
    params = {}
    for key in ["exercise_name", "category", "muscle_group", "duration_minutes", "calories_burned"]:
        value = data.get(key)
        if value is None:
            continue
        if key in {"duration_minutes", "calories_burned"} and value == "":
            continue
        params[key] = value
    return urlencode(params)


@login_required
def home(request):
    today = date.today()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    workouts = Workout.objects.filter(user=request.user).order_by("-performed_on", "-id")[:5]
    calories_in = (
        FoodEntry.objects.filter(user=request.user, consumed_at__date=today).aggregate(total=Sum("calories"))[
            "total"
        ]
        or 0
    )
    calories_out = (
        ExerciseEntry.objects.filter(user=request.user, workout__performed_on=today).aggregate(
            total=Sum("calories_burned")
        )["total"]
        or 0
    )
    water_total = (
        WaterEntry.objects.filter(user=request.user, consumed_at__date=today).aggregate(total=Sum("amount_ml"))[
            "total"
        ]
        or 0
    )
    goals = Goal.objects.filter(user=request.user, active=True).order_by("end_date")[:5]
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:5]
    recommended_calories = profile.estimated_daily_calories()
    water_goal_ml = profile.daily_water_goal_ml or 3000
    water_progress_pct = min(100, round((float(water_total) / float(water_goal_ml)) * 100, 1)) if water_goal_ml else 0

    context = {
        "workouts": workouts,
        "calories_in": calories_in,
        "calories_out": calories_out,
        "net_calories": calories_in - calories_out,
        "recommended_calories": recommended_calories,
        "water_total": water_total,
        "water_goal_ml": water_goal_ml,
        "water_progress_pct": water_progress_pct,
        "goals": goals,
        "notifications": notifications,
    }
    context.update(_dashboard_charts(
        request.user, today,
        water_goal_ml=water_goal_ml,
        recommended_calories=recommended_calories,
    ))
    return render(request, "workouts/home.html", context)


@login_required
def workout_list(request):
    period = request.GET.get("period", "week")
    period, start, end, prev_start, prev_end = _workout_period(period)
    workouts = Workout.objects.filter(user=request.user, performed_on__range=(start, end)).order_by("-performed_on", "-id")
    period_minutes = (
        ExerciseEntry.objects.filter(user=request.user, workout__performed_on__range=(start, end)).aggregate(
            total=Sum("duration_minutes")
        )["total"]
        or 0
    )
    previous_minutes = (
        ExerciseEntry.objects.filter(
            user=request.user, workout__performed_on__range=(prev_start, prev_end)
        ).aggregate(total=Sum("duration_minutes"))["total"]
        or 0
    )
    period_calories = (
        ExerciseEntry.objects.filter(user=request.user, workout__performed_on__range=(start, end)).aggregate(
            total=Sum("calories_burned")
        )["total"]
        or 0
    )
    trend_delta = float(period_minutes) - float(previous_minutes)
    return render(
        request,
        "workouts/workout_list.html",
        {
            "workouts": workouts,
            "period": period,
            "period_minutes": period_minutes,
            "previous_minutes": previous_minutes,
            "period_calories": period_calories,
            "trend_delta": trend_delta,
        },
    )


@login_required
def workout_add(request):
    if request.method == "POST":
        form = WorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        form = WorkoutForm()
    return render(request, "workouts/workout_form.html", {"form": form})


@login_required
def workout_edit(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    if request.method == "POST":
        form = WorkoutForm(request.POST, instance=workout)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.user = request.user
            edited.save()
            messages.success(request, "Workout updated.")
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        form = WorkoutForm(instance=workout)
    return render(request, "workouts/workout_form.html", {"form": form, "mode": "edit"})


@login_required
def workout_delete(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    if request.method == "POST":
        workout.delete()
        messages.success(request, "Workout deleted.")
    return redirect("workouts:list")


@login_required
def workout_detail(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    return render(request, "workouts/workout_detail.html", {"workout": workout})


@login_required
def exercise_add(request, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    if request.method == "POST":
        if "ai_estimate" in request.POST:
            form = ExerciseEntryForm(request.POST)
            if form.is_valid():
                estimate_candidate = form.save(commit=False)
                _populate_classification(estimate_candidate)
                ai_used = _estimate_calories_with_ai_or_fallback(exercise=estimate_candidate, user=request.user)
                prefill = {
                    "exercise_name": estimate_candidate.exercise_name,
                    "category": estimate_candidate.category or "",
                    "muscle_group": estimate_candidate.muscle_group or "",
                    "duration_minutes": estimate_candidate.duration_minutes,
                    "calories_burned": estimate_candidate.calories_burned,
                }
                if ai_used:
                    messages.success(request, "AI estimate added to calories. You can edit before saving.")
                else:
                    messages.info(request, "AI unavailable. Used standard calorie estimate.")
                query = _exercise_prefill_query(prefill)
                url = reverse("workouts:exercise_add", kwargs={"workout_id": workout.id})
                if query:
                    url = f"{url}?{query}"
                return redirect(url)
            else:
                messages.error(request, "Please fix form errors before requesting AI estimate.")
                return render(
                    request,
                    "workouts/exercise_form.html",
                    {"form": form, "workout": workout},
                )

        form = ExerciseEntryForm(request.POST)
        if form.is_valid():
            exercise = form.save(commit=False)
            _populate_classification(exercise)
            _estimate_calories_with_ai_or_fallback(exercise=exercise, user=request.user)
            exercise.workout = workout
            exercise.user = request.user
            exercise.save()
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        initial = {}
        for key in ["exercise_name", "category", "muscle_group", "duration_minutes", "calories_burned"]:
            if key in request.GET:
                initial[key] = request.GET.get(key)
        form = ExerciseEntryForm(initial=initial)
    return render(
        request,
        "workouts/exercise_form.html",
        {"form": form, "workout": workout},
    )


@login_required
def exercise_edit(request, workout_id: int, exercise_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    exercise = get_object_or_404(ExerciseEntry, id=exercise_id, workout=workout, user=request.user)
    if request.method == "POST":
        if "ai_estimate" in request.POST:
            form = ExerciseEntryForm(request.POST, instance=exercise)
            if form.is_valid():
                estimate_candidate = form.save(commit=False)
                _populate_classification(estimate_candidate)
                ai_used = _estimate_calories_with_ai_or_fallback(exercise=estimate_candidate, user=request.user)
                prefill = {
                    "exercise_name": estimate_candidate.exercise_name,
                    "category": estimate_candidate.category or "",
                    "muscle_group": estimate_candidate.muscle_group or "",
                    "duration_minutes": estimate_candidate.duration_minutes,
                    "calories_burned": estimate_candidate.calories_burned,
                }
                if ai_used:
                    messages.success(request, "AI estimate added to calories. You can edit before saving.")
                else:
                    messages.info(request, "AI unavailable. Used standard calorie estimate.")
                query = _exercise_prefill_query(prefill)
                url = reverse("workouts:exercise_edit", kwargs={"workout_id": workout.id, "exercise_id": exercise.id})
                if query:
                    url = f"{url}?{query}"
                return redirect(url)
            else:
                messages.error(request, "Please fix form errors before requesting AI estimate.")
                return render(
                    request,
                    "workouts/exercise_form.html",
                    {"form": form, "workout": workout, "mode": "edit"},
                )

        form = ExerciseEntryForm(request.POST, instance=exercise)
        if form.is_valid():
            updated = form.save(commit=False)
            _populate_classification(updated)
            _estimate_calories_with_ai_or_fallback(exercise=updated, user=request.user)
            updated.user = request.user
            updated.workout = workout
            updated.save()
            messages.success(request, "Exercise updated.")
            return redirect("workouts:detail", workout_id=workout.id)
    else:
        initial = {}
        for key in ["exercise_name", "category", "muscle_group", "duration_minutes", "calories_burned"]:
            if key in request.GET:
                initial[key] = request.GET.get(key)
        form = ExerciseEntryForm(instance=exercise, initial=initial)
    return render(request, "workouts/exercise_form.html", {"form": form, "workout": workout, "mode": "edit"})


@login_required
def exercise_delete(request, workout_id: int, exercise_id: int):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    exercise = get_object_or_404(ExerciseEntry, id=exercise_id, workout=workout, user=request.user)
    if request.method == "POST":
        exercise.delete()
        messages.success(request, "Exercise deleted.")
    return redirect("workouts:detail", workout_id=workout.id)


@login_required
def exercise_library(request):
    q = (request.GET.get("q") or "").strip()
    items = ExerciseLibrary.objects.all()
    if q:
        items = items.filter(
            Q(name__icontains=q)
            | Q(category__icontains=q)
            | Q(muscle_group__icontains=q)
            | Q(description__icontains=q)
            | Q(instructions__icontains=q)
        )
    return render(request, "workouts/exercise_library.html", {"items": items, "q": q})


@login_required
def plan_list(request):
    plans = WorkoutPlan.objects.filter(user=request.user).order_by("-updated_at", "-id")
    return render(request, "workouts/plan_list.html", {"plans": plans})


@login_required
def plan_add(request):
    if request.method == "POST":
        form = WorkoutPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.save()
            messages.success(request, "Workout plan created.")
            return redirect("workouts:plan_list")
    else:
        form = WorkoutPlanForm()
    return render(request, "workouts/plan_form.html", {"form": form, "mode": "add"})


@login_required
def plan_edit(request, plan_id: int):
    plan = get_object_or_404(WorkoutPlan, id=plan_id, user=request.user)
    if request.method == "POST":
        form = WorkoutPlanForm(request.POST, instance=plan)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.user = request.user
            updated.save()
            messages.success(request, "Workout plan updated.")
            return redirect("workouts:plan_list")
    else:
        form = WorkoutPlanForm(instance=plan)
    return render(request, "workouts/plan_form.html", {"form": form, "mode": "edit"})


@login_required
def plan_delete(request, plan_id: int):
    plan = get_object_or_404(WorkoutPlan, id=plan_id, user=request.user)
    if request.method == "POST":
        plan.delete()
        messages.success(request, "Workout plan deleted.")
    return redirect("workouts:plan_list")
