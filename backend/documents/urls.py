from django.urls import path
from .views import DocumentDetailView, DocumentListView, DocumentUploadView, HealthCheckView, document_correction_view, document_export_view

urlpatterns = [
    path('health/', HealthCheckView.as_view()),
    path('documents/upload/', DocumentUploadView.as_view()),
    path('documents/', DocumentListView.as_view()),
    path('documents/<int:pk>/', DocumentDetailView.as_view()),
    path('documents/<int:pk>/export/', document_export_view),
    path('documents/<int:pk>/corrections/', document_correction_view),
]
