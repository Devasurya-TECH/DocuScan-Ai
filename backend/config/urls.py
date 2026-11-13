from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('documents.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='frontend-home'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        '/assets/',
        document_root=settings.FRONTEND_DIST_DIR / 'assets',
    )

# React Router routes are served by the same built application in local Django
# development. API, admin, media, and asset paths are matched above first.
urlpatterns += [
    re_path(r'^(?!api/|admin/|media/|assets/).*$', TemplateView.as_view(template_name='index.html')),
]
