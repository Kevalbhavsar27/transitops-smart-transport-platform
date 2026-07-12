from rest_framework.routers import DefaultRouter

from .api_views import (
    ExpenseViewSet,
    FuelLogViewSet,
    MaintenanceRecordViewSet,
    TripViewSet,
)


router = DefaultRouter()

router.register(
    "trips",
    TripViewSet,
    basename="trip",
)

router.register(
    "maintenance",
    MaintenanceRecordViewSet,
    basename="maintenance",
)

router.register(
    "fuel-logs",
    FuelLogViewSet,
    basename="fuel-log",
)

router.register(
    "expenses",
    ExpenseViewSet,
    basename="expense",
)


urlpatterns = router.urls