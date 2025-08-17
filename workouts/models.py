from django.conf import settings
from django.db import models
from django.utils import timezone


class Workout(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    difficulty = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def exercise_count(self) -> int:
        return self.exercises.count()


class Exercise(models.Model):
    title = models.CharField(max_length=200)
    how_to = models.TextField()
    reps = models.PositiveIntegerField()
    image = models.ImageField(upload_to='exercises/', blank=True, null=True)

    def __str__(self):
        return self.title


class WorkoutExercise(models.Model):
    workout = models.ForeignKey(Workout, related_name='workout_exercises', on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, related_name='in_workouts', on_delete=models.PROTECT)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']
        unique_together = [('workout', 'exercise')]

    def __str__(self):
        return f"{self.workout.name} -> {self.exercise.title} ({self.position})"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    timezone = models.CharField(max_length=64, default='Europe/Madrid')
    last_selected_workout = models.ForeignKey(Workout, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Profile({self.user.username})"


class Session(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In progress'),
        ('completed', 'Completed'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workout = models.ForeignKey(Workout, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    current_index = models.PositiveIntegerField(default=0)

    def finish(self):
        self.finished_at = timezone.now()
        self.status = 'completed'
        self.save(update_fields=['finished_at', 'status'])

    @property
    def duration_seconds(self) -> int:
        if not self.finished_at:
            return 0
        return int((self.finished_at - self.started_at).total_seconds())


class WorkoutHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_history')
    workout = models.ForeignKey(Workout, on_delete=models.PROTECT)
    performed_at = models.DateTimeField(default=timezone.now)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.user} - {self.workout} @ {self.performed_at}"
