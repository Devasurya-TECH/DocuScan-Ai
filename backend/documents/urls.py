from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    DocumentDetailView,
    DocumentListView,
    DocumentStatusView,
    DocumentUploadView,
    HealthCheckView,
    UserProfileView,
    UserRegisterView,
    benchmark_report_view,
    document_correction_view,
    document_export_view,
    document_file_download_view,
    document_qa_view,
    document_reprocess_view,
    document_autocorrect_view,
)

urlpatterns = [
    # System health
    path('health/', HealthCheckView.as_view(), name='health-check'),

    # Authentication & Profile
    path('auth/register/', UserRegisterView.as_view(), name='auth-register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='auth-token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/me/', UserProfileView.as_view(), name='auth-me'),

    # Document Processing & Management
    path('documents/upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:pk>/status/', DocumentStatusView.as_view(), name='document-status'),
    path('documents/<int:pk>/export/', document_export_view, name='document-export'),
    path('documents/<int:pk>/corrections/', document_correction_view, name='document-correction'),
    path('documents/<int:pk>/reprocess/', document_reprocess_view, name='document-reprocess'),
    path('documents/<int:pk>/autocorrect/', document_autocorrect_view, name='document-autocorrect'),

    # Advanced AI: RAG Question Answering & Secure File Access
    path('documents/<int:pk>/ask/', document_qa_view, name='document-qa'),
    path('documents/<int:pk>/file/<str:file_type>/', document_file_download_view, name='document-file-download'),

    # Evaluation Dashboard
    path('evaluation/benchmark/', benchmark_report_view, name='evaluation-benchmark'),
]
