from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
from django.http import JsonResponse


def health_check(request):
    """
    Lightweight, zero-dependency health check endpoint for Render, Docker,
    and external load balancers.
    Responds in <1ms without touching the database or loading ML/OCR models.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'docuscan-api',
        'version': '2.0.0',
    }, status=200)


urlpatterns = [
    # Top-level health endpoints (handles Render probes to /health/, /health, or /healthz)
    path('health/', health_check, name='root-health-check-slash'),
    path('health', health_check, name='root-health-check'),
    path('healthz', health_check, name='root-healthz'),

    path('admin/', admin.site.urls),
    path('api/', include('documents.urls')),
    re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': settings.FRONTEND_DIST_DIR / 'assets'}),
    # A persistent disk is mounted at MEDIA_ROOT in the production blueprint.
    # Put media behind object storage/CDN when horizontal scaling is introduced.
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('', TemplateView.as_view(template_name='index.html'), name='frontend-home'),
]

# React Router routes are served by the same built application in local Django
# development. API, admin, media, assets, and health paths are matched above first.
urlpatterns += [
    re_path(r'^(?!api/|admin/|media/|assets/|health).*$', TemplateView.as_view(template_name='index.html')),
]
