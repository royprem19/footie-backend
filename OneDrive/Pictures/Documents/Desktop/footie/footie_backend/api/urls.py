from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# THE FIX: Cleaned up duplicate imports and added 'leave_match'
from .views import (
    register_user, CustomTokenObtainPairView,
    UserViewSet, VenueViewSet, MatchViewSet, SquadViewSet,
    join_match, leave_match
)

# A Router automatically builds all the URLs for getting, creating, and deleting data!
router = DefaultRouter()
router.register(r'venues', VenueViewSet)
router.register(r'matches', MatchViewSet)
router.register(r'users', UserViewSet)
router.register(r'squads', SquadViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', register_user, name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('matches/<int:pk>/join/', join_match, name='join_match'),
    path('matches/<int:pk>/leave/', leave_match, name='leave_match'), # <--- THE FIX IS HERE!
]