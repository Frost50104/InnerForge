from django.urls import path
from . import views

app_name = 'workouts'

urlpatterns = [
    path('list/', views.workout_list, name='list'),
    path('select/<int:pk>/', views.select_workout, name='select'),
    path('start/', views.start_workout, name='start'),
    path('session/<int:session_id>/', views.session_step, name='session_step'),
    path('session/<int:session_id>/next/', views.session_next, name='session_next'),
    path('congrats/', views.congrats, name='congrats'),
    path('history/', views.history, name='history'),

    # Admin-like CRUD (behind is_staff)
    path('admin/new/', views.workout_create, name='create'),
    path('admin/<int:pk>/edit/', views.workout_edit, name='edit'),
    path('admin/<int:pk>/archive/', views.workout_archive, name='archive'),
    path('admin/<int:workout_id>/exercise/add/', views.exercise_add, name='exercise_add'),
    path('admin/<int:workout_id>/exercise/<int:we_id>/delete/', views.exercise_delete, name='exercise_delete'),
]
