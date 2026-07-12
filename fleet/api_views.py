from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.api_permissions import roles_required
from accounts.models import User

from .models import Driver, Vehicle
from .serializers import DriverSerializer, VehicleSerializer


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Vehicle.objects.all()

        search = self.request.query_params.get(
            "search",
            "",
        ).strip()

        vehicle_status = self.request.query_params.get(
            "status",
            "",
        ).strip()

        vehicle_type = self.request.query_params.get(
            "vehicle_type",
            "",
        ).strip()

        region = self.request.query_params.get(
            "region",
            "",
        ).strip()

        if search:
            queryset = queryset.filter(
                Q(registration_number__icontains=search)
                | Q(vehicle_name__icontains=search)
                | Q(model__icontains=search)
            )

        if vehicle_status:
            queryset = queryset.filter(
                status=vehicle_status
            )

        if vehicle_type:
            queryset = queryset.filter(
                vehicle_type=vehicle_type
            )

        if region:
            queryset = queryset.filter(
                region__icontains=region
            )

        return queryset

    def get_permissions(self):
        permissions = [IsAuthenticated()]

        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.FLEET_MANAGER,
            )

            permissions.append(permission_class())

        elif self.action == "destroy":
            permission_class = roles_required(
                User.Role.ADMIN,
            )

            permissions.append(permission_class())

        return permissions

    def destroy(self, request, *args, **kwargs):
        vehicle = self.get_object()

        if vehicle.status in [
            Vehicle.Status.ON_TRIP,
            Vehicle.Status.IN_SHOP,
        ]:
            return Response(
                {
                    "detail": (
                        "An active or maintained vehicle "
                        "cannot be deleted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(
            request,
            *args,
            **kwargs,
        )


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Driver.objects.all()

        search = self.request.query_params.get(
            "search",
            "",
        ).strip()

        driver_status = self.request.query_params.get(
            "status",
            "",
        ).strip()

        category = self.request.query_params.get(
            "license_category",
            "",
        ).strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(license_number__icontains=search)
                | Q(contact_number__icontains=search)
            )

        if driver_status:
            queryset = queryset.filter(
                status=driver_status
            )

        if category:
            queryset = queryset.filter(
                license_category__icontains=category
            )

        return queryset

    def get_permissions(self):
        permissions = [IsAuthenticated()]

        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.DISPATCHER,
                User.Role.SAFETY_OFFICER,
            )

            permissions.append(permission_class())

        elif self.action == "destroy":
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.SAFETY_OFFICER,
            )

            permissions.append(permission_class())

        return permissions

    def destroy(self, request, *args, **kwargs):
        driver = self.get_object()

        if driver.status == Driver.Status.ON_TRIP:
            return Response(
                {
                    "detail": (
                        "A driver currently on a trip "
                        "cannot be deleted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(
            request,
            *args,
            **kwargs,
        )