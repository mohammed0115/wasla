from django.urls import path

from .views import AICategorizeAPI, AIDescriptionAPI, AIVisualSearchAPI


urlpatterns = [
    path("ai/description", AIDescriptionAPI.as_view(), name="ai_description"),
    path("ai/categorize", AICategorizeAPI.as_view(), name="ai_categorize"),
    path("ai/visual-search", AIVisualSearchAPI.as_view(), name="ai_visual_search"),
]
