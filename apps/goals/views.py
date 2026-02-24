from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect, render

from .forms import GoalForm
from .models import Goal
from .services import calculate_goal_progress, recommend_exercises_for_goal


@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user).order_by("-active", "end_date")
    for goal in goals:
        goal.current_progress = calculate_goal_progress(goal)
        goal.recommended_exercises = recommend_exercises_for_goal(goal.goal_type, limit=3)
    return render(request, "goals/goal_list.html", {"goals": goals})


@login_required
def goal_add(request):
    if request.method == "POST":
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect("goals:list")
    else:
        form = GoalForm()
    return render(request, "goals/goal_form.html", {"form": form})


@login_required
def goal_edit(request, goal_id: int):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, "Goal updated.")
            return redirect("goals:list")
    else:
        form = GoalForm(instance=goal)
    return render(request, "goals/goal_form.html", {"form": form, "mode": "edit"})


@login_required
def goal_delete(request, goal_id: int):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    if request.method == "POST":
        goal.delete()
        messages.success(request, "Goal deleted.")
    return redirect("goals:list")
