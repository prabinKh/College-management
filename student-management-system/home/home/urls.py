from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('school.urls')),  
    path('student/',include('student.urls' , namespace='students')),
    path('authentication/',include('home_auth.urls')),
    path('teachers/',include('teachers.urls')),
    path('department/',include('department.urls')),
    path('subjects/', include('subjects.urls')),
    path('semesters/', include('semesters.urls', namespace='semesters')),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
