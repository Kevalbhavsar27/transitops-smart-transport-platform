from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.api_permissions import roles_required
from accounts.models import User

from .models import Expense, FuelLog, MaintenanceRecord, Trip
from .serializers import (
    ExpenseSerializer,
    FuelLogSerializer,
    MaintenanceCloseSerializer,
    MaintenanceRecordSerializer,
    TripCompleteSerializer,
    TripSerializer,
)
from .services import (
    cancel_maintenance,
    cancel_trip,
    close_maintenance,
    complete_trip,
    dispatch_trip,
    open_maintenance,
)


def validation_error_details(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {
        "detail": error.messages,
    }


class TripViewSet(viewsets.ModelViewSet):
    queryset = (
        Trip.objects
        .select_related(
            "vehicle",
            "driver",
            "created_by",
        )
        .all()
    )

    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset

        search = self.request.query_params.get(
            "search",
            "",
        ).strip()

        trip_status = self.request.query_params.get(
            "status",
            "",
        ).strip()

        vehicle_id = self.request.query_params.get(
            "vehicle",
            "",
        ).strip()

        driver_id = self.request.query_params.get(
            "driver",
            "",
        ).strip()

        if search:
            queryset = queryset.filter(
                Q(source__icontains=search)
                | Q(destination__icontains=search)
                | Q(
                    vehicle__registration_number__icontains=search
                )
                | Q(driver__name__icontains=search)
            )

        if trip_status:
            queryset = queryset.filter(
                status=trip_status
            )

        if vehicle_id:
            queryset = queryset.filter(
                vehicle_id=vehicle_id
            )

        if driver_id:
            queryset = queryset.filter(
                driver_id=driver_id
            )

        return queryset

    def get_permissions(self):
        permissions = [IsAuthenticated()]

        write_actions = [
            "create",
            "update",
            "partial_update",
            "dispatch",
            "complete",
            "cancel",
        ]

        if self.action in write_actions:
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.DISPATCHER,
            )

            permissions.append(permission_class())

        elif self.action == "destroy":
            permission_class = roles_required(
                User.Role.ADMIN,
            )

            permissions.append(permission_class())

        return permissions

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user
        )

    def destroy(self, request, *args, **kwargs):
        trip = self.get_object()

        if trip.status not in [
            Trip.Status.DRAFT,
            Trip.Status.CANCELLED,
        ]:
            return Response(
                {
                    "detail": (
                        "Only Draft or Cancelled trips "
                        "can be deleted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(
            request,
            *args,
            **kwargs,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="dispatch",
    )
    def dispatch(self, request, pk=None):
        trip = self.get_object()

        try:
            trip = dispatch_trip(trip.pk)

        except DjangoValidationError as error:
            return Response(
                validation_error_details(error),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TripSerializer(
            trip,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):
        trip = self.get_object()

        input_serializer = TripCompleteSerializer(
            data=request.data
        )

        input_serializer.is_valid(
            raise_exception=True
        )

        try:
            trip = complete_trip(
                trip.pk,
                input_serializer.validated_data[
                    "final_odometer"
                ],
                input_serializer.validated_data[
                    "fuel_consumed"
                ],
            )

        except DjangoValidationError as error:
            return Response(
                validation_error_details(error),
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = TripSerializer(
            trip,
            context={
                "request": request,
            },
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        trip = self.get_object()

        try:
            trip = cancel_trip(trip.pk)

        except DjangoValidationError as error:
            return Response(
                validation_error_details(error),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TripSerializer(
            trip,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    queryset = (
        MaintenanceRecord.objects
        .select_related(
            "vehicle",
            "created_by",
        )
        .all()
    )

    serializer_class = MaintenanceRecordSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    def get_queryset(self):
        queryset = self.queryset

        status_value = self.request.query_params.get(
            "status",
            "",
        ).strip()

        vehicle_id = self.request.query_params.get(
            "vehicle",
            "",
        ).strip()

        priority = self.request.query_params.get(
            "priority",
            "",
        ).strip()

        if status_value:
            queryset = queryset.filter(
                status=status_value
            )

        if vehicle_id:
            queryset = queryset.filter(
                vehicle_id=vehicle_id
            )

        if priority:
            queryset = queryset.filter(
                priority=priority
            )

        return queryset

    def get_permissions(self):
        permissions = [IsAuthenticated()]

        if self.action in [
            "create",
            "close",
            "cancel",
        ]:
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.FLEET_MANAGER,
            )

            permissions.append(
                permission_class()
            )

        return permissions

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        try:
            record = open_maintenance(
                vehicle=data["vehicle"],
                maintenance_type=data[
                    "maintenance_type"
                ],
                description=data["description"],
                priority=data["priority"],
                estimated_cost=data.get(
                    "estimated_cost",
                    0,
                ),
                expected_completion_date=data.get(
                    "expected_completion_date"
                ),
                created_by=request.user,
            )

        except DjangoValidationError as error:
            return Response(
                validation_error_details(error),
                status=status.HTTP_400_BAD_REQUEST,
            )

        output = self.get_serializer(record)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="close",
    )
    def close(self, request, pk=None):
        record = self.get_object()

        serializer = MaintenanceCloseSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            record = close_maintenance(
                record.pk,
                serializer.validated_data[
                    "final_cost"
                ],
                serializer.validated_data.get(
                    "completion_notes",
                    "",
                ),
            )

        except DjangoValidationError as error:
            return Response(
                validation_error_details(error),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            MaintenanceRecordSerializer(record).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        record = self.get_object()

        try:
            record = cancel_maintenance(
                record.pk
            )

        except DjangoValidationError as error:
            return Response(
                validation_error_details(error),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            MaintenanceRecordSerializer(record).data
        )


class FuelLogViewSet(viewsets.ModelViewSet):
    queryset = (
        FuelLog.objects
        .select_related(
            "vehicle",
            "trip",
            "created_by",
        )
        .all()
    )

    serializer_class = FuelLogSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        queryset = self.queryset

        vehicle_id = self.request.query_params.get(
            "vehicle",
            "",
        ).strip()

        trip_id = self.request.query_params.get(
            "trip",
            "",
        ).strip()

        if vehicle_id:
            queryset = queryset.filter(
                vehicle_id=vehicle_id
            )

        if trip_id:
            queryset = queryset.filter(
                trip_id=trip_id
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
                User.Role.FINANCIAL_ANALYST,
            )

            permissions.append(
                permission_class()
            )

        elif self.action == "destroy":
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.FINANCIAL_ANALYST,
            )

            permissions.append(
                permission_class()
            )

        return permissions

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user
        )


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = (
        Expense.objects
        .select_related(
            "vehicle",
            "trip",
            "created_by",
        )
        .all()
    )

    serializer_class = ExpenseSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        queryset = self.queryset

        vehicle_id = self.request.query_params.get(
            "vehicle",
            "",
        ).strip()

        expense_type = self.request.query_params.get(
            "expense_type",
            "",
        ).strip()

        if vehicle_id:
            queryset = queryset.filter(
                vehicle_id=vehicle_id
            )

        if expense_type:
            queryset = queryset.filter(
                expense_type=expense_type
            )

        return queryset

    def get_permissions(self):
        permissions = [IsAuthenticated()]

        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            permission_class = roles_required(
                User.Role.ADMIN,
                User.Role.FINANCIAL_ANALYST,
            )

            permissions.append(
                permission_class()
            )

        return permissions

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user
        )