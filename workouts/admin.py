from django.contrib import admin
from .models import Workout, Exercise, WorkoutExercise, Session, WorkoutHistory, UserProfile


class WorkoutExerciseInline(admin.TabularInline):
    model = WorkoutExercise
    extra = 0


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'exercise_count')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [WorkoutExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('title', 'reps')
    search_fields = ('title',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'workout', 'status', 'started_at', 'finished_at', 'current_index')
    list_filter = ('status',)


@admin.register(WorkoutHistory)
class WorkoutHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'workout', 'performed_at', 'duration_seconds')
    list_filter = ('performed_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'timezone', 'last_selected_workout')
