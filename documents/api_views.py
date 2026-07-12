from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.api_permissions import roles_required
from accounts.models import User

from .models import VehicleDocument
from .serializers import VehicleDocumentSerializer


class VehicleDocumentViewSet(viewsets.ModelViewSet):
    queryset = VehicleDocument.objects.select_related(
        "vehicle",
        "uploaded_by",
    )
    serializer_class = VehicleDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        vehicle_id = self.request.query_params.get("vehicle")
        document_type = self.request.query_params.get("document_type")

        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        return queryset

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.action in {
            "create",
            "update",
            "partial_update",
            "destroy",
        }:
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.FLEET_MANAGER,
                User.Role.SAFETY_OFFICER,
            )
            permissions.append(permission_class())
        return permissions

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
