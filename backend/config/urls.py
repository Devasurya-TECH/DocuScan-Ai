from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('documents.urls')),
    re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': settings.FRONTEND_DIST_DIR / 'assets'}),
    # A persistent disk is mounted at MEDIA_ROOT in the production blueprint.
    # Put media behind object storage/CDN when horizontal scaling is introduced.
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('', TemplateView.as_view(template_name='index.html'), name='frontend-home'),
]

# React Router routes are served by the same built application in local Django
# development. API, admin, media, and asset paths are matched above first.
urlpatterns += [
    re_path(r'^(?!api/|admin/|media/|assets/).*$', TemplateView.as_view(template_name='index.html')),
]
