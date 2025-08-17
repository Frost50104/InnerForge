from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from workouts import views as wv

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', wv.signup, name='signup'),
    path('', wv.home, name='home'),
    path('workouts/', include('workouts.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
