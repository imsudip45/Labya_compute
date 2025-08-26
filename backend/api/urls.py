from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RenterViewSet,
    HostViewSet,
    WalletViewSet,
    TransactionViewSet,
    GPUViewSet,
    SessionViewSet,
    DashboardStatsView,
    AvailableGPUsView,
    RegisterRenterView,
    RegisterHostView,
    EmailTokenObtainPairView,
)

router = DefaultRouter()
router.register(r'renters', RenterViewSet, basename='renter')
router.register(r'hosts', HostViewSet, basename='host')
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'gpus', GPUViewSet, basename='gpu')
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = [
    # Custom endpoints (must come before router to avoid conflicts)
    path('gpus/available/', AvailableGPUsView.as_view(), name='available-gpus'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    # JWT Authentication endpoints (email-based login)
    path('auth/login/', EmailTokenObtainPairView.as_view(), name='jwt-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/register/renter/', RegisterRenterView.as_view(), name='register-renter'),
    path('auth/register/host/', RegisterHostView.as_view(), name='register-host'),
    # Router endpoints (must come last)
    path('', include(router.urls)),
]
