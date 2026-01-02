from django.urls import path

from .views import RecommendedListingsView

urlpatterns = [
    path("lands/", RecommendedListingsView.as_view(), name="recommend-lands"),
]
