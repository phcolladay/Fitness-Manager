from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import GoalForm
from .models import Goal
from .services import calculate_goal_progress


@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user).order_by("-active", "end_date")
    for goal in goals:
        goal.current_progress = calculate_goal_progress(goal)
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
