from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

# Cleaned up duplicate imports and added 'leave_match'
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
    # Custom Auth Paths
    path('auth/register/', register_user, name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Custom Match Paths
    path('matches/<int:pk>/join/', join_match, name='join_match'),
    path('matches/<int:pk>/leave/', leave_match, name='leave_match'),
    
    # Custom Leaderboard Path
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    
    # Custom Squad Paths (These MUST come before the router!)
    path('squads/create/', views.create_squad, name='create_squad'),
    path('squads/<int:squad_id>/join/', views.join_squad, name='join_squad'),
    path('squads/leave/', views.leave_squad, name='leave_squad'),
    path('squads/all/', views.get_squads, name='get_squads'), # slightly renamed to prevent conflict

    # THE FIX: Move the router to the very bottom so it acts as a fallback!
    path('', include(router.urls)),
]