from django.urls import path
from .views import AnalyzeView, ExtractTextView

urlpatterns = [
    path('analyze/', AnalyzeView.as_view(), name='analyze'),
    path('extract-text/', ExtractTextView.as_view(), name='extract-text'),
]