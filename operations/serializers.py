from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from fleet.models import Driver, Vehicle

from .models import *


class VehicleSummarySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Vehicle

        fields = [
            "id",
            "registration_number",
            "vehicle_name",
            "maximum_load_capacity",
            "odometer",
            "status",
        ]


class DriverSummarySerializer(
    serializers.ModelSerializer
):
    is_license_expired = serializers.ReadOnlyField()

    class Meta:
        model = Driver

        fields = [
            "id",
            "name",
            "license_number",
            "license_expiry_date",
            "status",
            "is_license_expired",
        ]


class TripSerializer(serializers.ModelSerializer):
    vehicle = VehicleSummarySerializer(
        read_only=True
    )

    driver = DriverSummarySerializer(
        read_only=True
    )

    vehicle_id = serializers.PrimaryKeyRelatedField(
        queryset=Vehicle.objects.all(),
        source="vehicle",
        write_only=True,
    )

    driver_id = serializers.PrimaryKeyRelatedField(
        queryset=Driver.objects.all(),
        source="driver",
        write_only=True,
    )

    status_display = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()

    actual_distance = serializers.ReadOnlyField()
    fuel_efficiency = serializers.ReadOnlyField()

    class Meta:
        model = Trip

        fields = [
            "id",
            "source",
            "destination",
            "vehicle",
            "vehicle_id",
            "driver",
            "driver_id",
            "cargo_weight",
            "planned_distance",
            "start_odometer",
            "final_odometer",
            "fuel_consumed",
            "actual_distance",
            "fuel_efficiency",
            "revenue",
            "notes",
            "status",
            "status_display",
            "created_by_email",
            "created_at",
            "updated_at",
            "dispatched_at",
            "completed_at",
            "cancelled_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "start_odometer",
            "final_odometer",
            "fuel_consumed",
            "actual_distance",
            "fuel_efficiency",
            "created_at",
            "updated_at",
            "dispatched_at",
            "completed_at",
            "cancelled_at",
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_created_by_email(self, obj):
        if obj.created_by:
            return obj.created_by.email

        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if (
            self.instance
            and self.instance.status
            != Trip.Status.DRAFT
        ):
            raise serializers.ValidationError(
                "Only Draft trips can be edited."
            )

        vehicle = attrs.get(
            "vehicle",
            getattr(self.instance, "vehicle", None),
        )

        driver = attrs.get(
            "driver",
            getattr(self.instance, "driver", None),
        )

        cargo_weight = attrs.get(
            "cargo_weight",
            getattr(
                self.instance,
                "cargo_weight",
                None,
            ),
        )

        source = attrs.get(
            "source",
            getattr(self.instance, "source", ""),
        )

        destination = attrs.get(
            "destination",
            getattr(
                self.instance,
                "destination",
                "",
            ),
        )

        if (
            source
            and destination
            and source.strip().lower()
            == destination.strip().lower()
        ):
            raise serializers.ValidationError(
                {
                    "destination": (
                        "Source and destination cannot be the same."
                    )
                }
            )

        if (
            vehicle
            and vehicle.status
            != Vehicle.Status.AVAILABLE
        ):
            raise serializers.ValidationError(
                {
                    "vehicle_id": (
                        "The selected vehicle is not available."
                    )
                }
            )

        if (
            vehicle
            and cargo_weight
            and cargo_weight
            > vehicle.maximum_load_capacity
        ):
            raise serializers.ValidationError(
                {
                    "cargo_weight": (
                        f"Maximum capacity is "
                        f"{vehicle.maximum_load_capacity} kg."
                    )
                }
            )

        if driver:
            if driver.status != Driver.Status.AVAILABLE:
                raise serializers.ValidationError(
                    {
                        "driver_id": (
                            "The selected driver is not available."
                        )
                    }
                )

            if (
                driver.license_expiry_date
                < timezone.localdate()
            ):
                raise serializers.ValidationError(
                    {
                        "driver_id": (
                            "The selected driver's licence "
                            "has expired."
                        )
                    }
                )

        return attrs


class TripCompleteSerializer(serializers.Serializer):
    final_odometer = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
    )

    fuel_consumed = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

class MaintenanceRecordSerializer(
    serializers.ModelSerializer
):
    vehicle = VehicleSummarySerializer(
        read_only=True
    )

    vehicle_id = serializers.PrimaryKeyRelatedField(
        queryset=Vehicle.objects.all(),
        source="vehicle",
        write_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    priority_display = serializers.CharField(
        source="get_priority_display",
        read_only=True,
    )

    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceRecord

        fields = [
            "id",
            "vehicle",
            "vehicle_id",
            "maintenance_type",
            "description",
            "priority",
            "priority_display",
            "estimated_cost",
            "final_cost",
            "expected_completion_date",
            "status",
            "status_display",
            "completion_notes",
            "created_by_email",
            "created_at",
            "updated_at",
            "completed_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "final_cost",
            "completion_notes",
            "created_at",
            "updated_at",
            "completed_at",
        ]

    def get_created_by_email(self, obj):
        if obj.created_by:
            return obj.created_by.email

        return None

    def validate_vehicle_id(self, vehicle):
        if vehicle.status != Vehicle.Status.AVAILABLE:
            raise serializers.ValidationError(
                "Only an available vehicle can enter maintenance."
            )

        return vehicle


class MaintenanceCloseSerializer(serializers.Serializer):
    final_cost = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0"),
    )

    completion_notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class FuelLogSerializer(serializers.ModelSerializer):
    vehicle = VehicleSummarySerializer(
        read_only=True
    )

    vehicle_id = serializers.PrimaryKeyRelatedField(
        queryset=Vehicle.objects.all(),
        source="vehicle",
        write_only=True,
    )

    trip_id = serializers.PrimaryKeyRelatedField(
        queryset=Trip.objects.all(),
        source="trip",
        required=False,
        allow_null=True,
    )

    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = FuelLog

        fields = [
            "id",
            "vehicle",
            "vehicle_id",
            "trip_id",
            "date",
            "liters",
            "price_per_liter",
            "total_cost",
            "odometer",
            "notes",
            "created_by_email",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "total_cost",
            "created_at",
            "updated_at",
        ]

    def get_created_by_email(self, obj):
        if obj.created_by:
            return obj.created_by.email

        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)

        vehicle = attrs.get(
            "vehicle",
            getattr(self.instance, "vehicle", None),
        )

        trip = attrs.get(
            "trip",
            getattr(self.instance, "trip", None),
        )

        odometer = attrs.get(
            "odometer",
            getattr(self.instance, "odometer", None),
        )

        if trip and vehicle and trip.vehicle_id != vehicle.id:
            raise serializers.ValidationError(
                {
                    "trip_id": (
                        "This trip does not belong "
                        "to the selected vehicle."
                    )
                }
            )

        if (
            vehicle
            and odometer is not None
            and odometer < vehicle.odometer
        ):
            raise serializers.ValidationError(
                {
                    "odometer": (
                        f"Odometer cannot be below "
                        f"{vehicle.odometer} km."
                    )
                }
            )

        return attrs


class ExpenseSerializer(serializers.ModelSerializer):
    vehicle = VehicleSummarySerializer(
        read_only=True
    )

    vehicle_id = serializers.PrimaryKeyRelatedField(
        queryset=Vehicle.objects.all(),
        source="vehicle",
        write_only=True,
    )

    trip_id = serializers.PrimaryKeyRelatedField(
        queryset=Trip.objects.all(),
        source="trip",
        required=False,
        allow_null=True,
    )

    expense_type_display = serializers.CharField(
        source="get_expense_type_display",
        read_only=True,
    )

    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Expense

        fields = [
            "id",
            "vehicle",
            "vehicle_id",
            "trip_id",
            "expense_type",
            "expense_type_display",
            "description",
            "amount",
            "date",
            "created_by_email",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_created_by_email(self, obj):
        if obj.created_by:
            return obj.created_by.email

        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)

        vehicle = attrs.get(
            "vehicle",
            getattr(self.instance, "vehicle", None),
        )

        trip = attrs.get(
            "trip",
            getattr(self.instance, "trip", None),
        )

        if trip and vehicle and trip.vehicle_id != vehicle.id:
            raise serializers.ValidationError(
                {
                    "trip_id": (
                        "This trip does not belong "
                        "to the selected vehicle."
                    )
                }
            )

        return attrs