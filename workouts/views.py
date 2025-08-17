from datetime import timedelta
from calendar import day_abbr
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings

from .forms import WorkoutForm, ExerciseForm, WorkoutExerciseForm
from .models import Workout, WorkoutExercise, Exercise, Session, WorkoutHistory, UserProfile


def _get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _week_range(dt, tz):
    # Return Monday 00:00 to Sunday 23:59:59 in given tz
    local_dt = dt.astimezone(tz)
    monday = (local_dt - timedelta(days=(local_dt.weekday()))).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday_end = monday + timedelta(days=7) - timedelta(seconds=1)
    return monday, sunday_end


def home(request: HttpRequest) -> HttpResponse:
    user = request.user
    selected_workout = None
    done_days = set()

    if user.is_authenticated:
        profile = _get_or_create_profile(user)
        selected_workout = profile.last_selected_workout

        # Week highlight
        tzname = profile.timezone or 'Europe/Madrid'
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            tz = ZoneInfo(getattr(settings, 'TIME_ZONE', 'UTC'))
        now = timezone.now().astimezone(tz)
        start, end = _week_range(now, tz)
        qs = WorkoutHistory.objects.filter(user=user, performed_at__range=(start, end))
        for wh in qs:
            d = wh.performed_at.astimezone(tz).date()
            done_days.add(d)

    # Build week labels
    try:
        tz = ZoneInfo(getattr(settings, 'TIME_ZONE', 'Europe/Madrid'))
    except Exception:
        tz = ZoneInfo('UTC')
    now = timezone.now().astimezone(tz)
    monday, _ = _week_range(now, tz)
    week_days = []
    for i in range(7):
        day = (monday + timedelta(days=i))
        week_days.append({
            'label': day.strftime('%a'),
            'date': day.date(),
            'is_today': day.date() == now.date(),
            'is_done': day.date() in done_days,
        })

    context = {
        'week_days': week_days,
        'selected_workout': selected_workout,
    }
    return render(request, 'workouts/home.html', context)


@login_required
def workout_list(request: HttpRequest) -> HttpResponse:
    q = request.GET.get('q', '').strip()
    workouts = Workout.objects.filter(is_active=True)
    if q:
        workouts = workouts.filter(name__icontains=q)
    workouts = workouts.annotate(ex_count=Count('workout_exercises'))
    return render(request, 'workouts/workout_list.html', {'workouts': workouts, 'q': q})


@login_required
def select_workout(request: HttpRequest, pk: int):
    workout = get_object_or_404(Workout, pk=pk, is_active=True)
    profile = _get_or_create_profile(request.user)
    profile.last_selected_workout = workout
    profile.save(update_fields=['last_selected_workout'])
    messages.success(request, f'Вы выбрали тренировку: {workout.name}')
    return redirect('home')


@login_required
def start_workout(request: HttpRequest):
    profile = _get_or_create_profile(request.user)
    workout = profile.last_selected_workout
    if not workout:
        messages.info(request, 'Сначала выберите тренировку')
        return redirect('workouts:list')

    exercises = list(WorkoutExercise.objects.filter(workout=workout).order_by('position'))
    if not exercises:
        messages.error(request, 'В тренировке нет упражнений')
        return redirect('home')

    session = Session.objects.create(user=request.user, workout=workout, status='in_progress', current_index=0)
    return redirect('workouts:session_step', session_id=session.id)


@login_required
def session_step(request: HttpRequest, session_id: int):
    session = get_object_or_404(Session, id=session_id, user=request.user)
    exercises = list(WorkoutExercise.objects.filter(workout=session.workout).order_by('position'))
    if session.current_index >= len(exercises):
        return redirect('workouts:congrats')
    current = exercises[session.current_index]
    last = session.current_index == len(exercises) - 1
    return render(request, 'workouts/session_step.html', {
        'session': session,
        'current': current,
        'is_last': last,
    })


@login_required
def session_next(request: HttpRequest, session_id: int):
    session = get_object_or_404(Session, id=session_id, user=request.user)
    exercises = list(WorkoutExercise.objects.filter(workout=session.workout).order_by('position'))
    session.current_index += 1
    if session.current_index >= len(exercises):
        # finish
        session.finish()
        WorkoutHistory.objects.create(
            user=request.user,
            workout=session.workout,
            performed_at=timezone.now(),
            duration_seconds=session.duration_seconds,
        )
        messages.success(request, 'Тренировка успешно завершена!')
        return redirect('workouts:congrats')
    session.save(update_fields=['current_index'])
    return redirect('workouts:session_step', session_id=session.id)


@login_required
def congrats(request: HttpRequest):
    return render(request, 'workouts/congrats.html')


def signup(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def history(request: HttpRequest):
    qs = WorkoutHistory.objects.filter(user=request.user)
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        qs = qs.filter(performed_at__date__gte=start)
    if end:
        qs = qs.filter(performed_at__date__lte=end)
    items = list(qs.order_by('-performed_at')[:100])
    return render(request, 'workouts/history.html', {'items': items, 'start': start or '', 'end': end or ''})


# Admin-like CRUD

def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required
@transaction.atomic
def workout_create(request: HttpRequest):
    if request.method == 'POST':
        form = WorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save()
            messages.success(request, 'Тренировка создана')
            if request.user.is_staff:
                return redirect('workouts:edit', pk=workout.id)
            else:
                return redirect('workouts:list')
    else:
        form = WorkoutForm()
    return render(request, 'workouts/workout_edit.html', {
        'form': form,
        'workout': None,
        'exercises': [],
    })


@user_passes_test(is_admin)
@transaction.atomic
def workout_edit(request: HttpRequest, pk: int):
    workout = get_object_or_404(Workout, pk=pk)
    if request.method == 'POST':
        form = WorkoutForm(request.POST, instance=workout)
        if form.is_valid():
            form.save()
            messages.success(request, 'Тренировка сохранена')
            return redirect('workouts:edit', pk=workout.id)
    else:
        form = WorkoutForm(instance=workout)

    wex = WorkoutExercise.objects.filter(workout=workout).select_related('exercise').order_by('position')
    return render(request, 'workouts/workout_edit.html', {
        'form': form,
        'workout': workout,
        'exercises': wex,
    })


@user_passes_test(is_admin)
def workout_archive(request: HttpRequest, pk: int):
    workout = get_object_or_404(Workout, pk=pk)
    workout.is_active = False
    workout.save(update_fields=['is_active'])
    messages.info(request, 'Тренировка архивирована')
    return redirect('workouts:list')


@user_passes_test(is_admin)
@transaction.atomic
def exercise_add(request: HttpRequest, workout_id: int):
    workout = get_object_or_404(Workout, id=workout_id)
    if request.method == 'POST':
        eform = ExerciseForm(request.POST, request.FILES)
        if eform.is_valid():
            ex = eform.save()
            position = (WorkoutExercise.objects.filter(workout=workout).aggregate(Count('id'))['id__count'])
            WorkoutExercise.objects.create(workout=workout, exercise=ex, position=position)
            messages.success(request, 'Упражнение добавлено')
            return redirect('workouts:edit', pk=workout.id)
    else:
        eform = ExerciseForm()
    return render(request, 'workouts/exercise_form.html', {'form': eform, 'workout': workout})


@user_passes_test(is_admin)
@transaction.atomic
def exercise_delete(request: HttpRequest, workout_id: int, we_id: int):
    workout = get_object_or_404(Workout, id=workout_id)
    we = get_object_or_404(WorkoutExercise, id=we_id, workout=workout)
    we.delete()
    messages.info(request, 'Упражнение удалено из тренировки')
    return redirect('workouts:edit', pk=workout.id)
