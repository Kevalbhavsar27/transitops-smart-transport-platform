from rest_framework.routers import DefaultRouter

from .api_views import VehicleDocumentViewSet


router = DefaultRouter()
router.register(
    "vehicle-documents",
    VehicleDocumentViewSet,
    basename="vehicle-document",
)

urlpatterns = router.urls
