from rest_framework.routers import DefaultRouter

from .api_views import DriverViewSet, VehicleViewSet


router = DefaultRouter()

router.register(
    "vehicles",
    VehicleViewSet,
    basename="vehicle",
)

router.register(
    "drivers",
    DriverViewSet,
    basename="driver",
)


urlpatterns = router.urls