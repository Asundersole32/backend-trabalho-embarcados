from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core.views import (
    SensorDataView, ActuatorDataView, AlertsDataView, ManualControlView,
    RegisterView, UserSensorLogsView, UserClassificationsView, UserAlertsView,
    SensorViewSet, ActuatorViewSet, UserProfileView, UserActuatorLogsView
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'sensors', SensorViewSet)
router.register(r'actuators', ActuatorViewSet)

urlpatterns = [
    # Endpoints públicos de ingestão (hardware)
    path('api/sensor-data', SensorDataView.as_view(), name='sensor-data'),
    path('api/actuator-data', ActuatorDataView.as_view(), name='actuator-data'),

    # Endpoint público de alertas (ou pode ser privado)
    path('api/alerts-data', AlertsDataView.as_view(), name='alerts-data'),

    # Controle manual (requer autenticação)
    path('api/manual-control', ManualControlView.as_view(), name='manual-control'),

    # Autenticação
    path('api/register', RegisterView.as_view(), name='register'),
    path('api/token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),

    # Getters privados (requer token JWT)
    path('api/my/sensor-logs', UserSensorLogsView.as_view(), name='my-sensor-logs'),
    path('api/my/classifications', UserClassificationsView.as_view(), name='my-classifications'),
    path('api/my/alerts', UserAlertsView.as_view(), name='my-alerts'),
    path('api/my/profile', UserProfileView.as_view(), name='my-profile'),
    path('api/my/actuator-logs', UserActuatorLogsView.as_view(), name='my-actuator-logs'),
    path('api/', include(router.urls))
]