from django.utils import timezone
from rest_framework import serializers

from .models import Driver, Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    vehicle_type_display = serializers.CharField(
        source="get_vehicle_type_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    can_be_dispatched = serializers.ReadOnlyField()

    class Meta:
        model = Vehicle

        fields = [
            "id",
            "registration_number",
            "vehicle_name",
            "model",
            "vehicle_type",
            "vehicle_type_display",
            "maximum_load_capacity",
            "odometer",
            "acquisition_cost",
            "region",
            "status",
            "status_display",
            "can_be_dispatched",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "can_be_dispatched",
        ]

    def validate_registration_number(self, value):
        value = value.upper().strip()

        queryset = Vehicle.objects.filter(
            registration_number__iexact=value
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A vehicle with this registration number already exists."
            )

        return value

    def validate_status(self, value):
        automatic_statuses = [
            Vehicle.Status.ON_TRIP,
            Vehicle.Status.IN_SHOP,
        ]

        if value in automatic_statuses:
            current_status = (
                self.instance.status
                if self.instance
                else None
            )

            if value != current_status:
                raise serializers.ValidationError(
                    "On Trip and In Shop are controlled by workflows."
                )

        return value


class DriverSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    is_license_expired = serializers.ReadOnlyField()
    can_be_dispatched = serializers.ReadOnlyField()

    class Meta:
        model = Driver

        fields = [
            "id",
            "name",
            "license_number",
            "license_category",
            "license_expiry_date",
            "contact_number",
            "safety_score",
            "status",
            "status_display",
            "is_license_expired",
            "can_be_dispatched",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "is_license_expired",
            "can_be_dispatched",
        ]

    def validate_license_number(self, value):
        value = value.upper().strip()

        queryset = Driver.objects.filter(
            license_number__iexact=value
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A driver with this licence number already exists."
            )

        return value

    def validate_status(self, value):
        if value == Driver.Status.ON_TRIP:
            current_status = (
                self.instance.status
                if self.instance
                else None
            )

            if current_status != Driver.Status.ON_TRIP:
                raise serializers.ValidationError(
                    "On Trip status is controlled by trip dispatch."
                )

        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        expiry_date = attrs.get(
            "license_expiry_date",
            getattr(
                self.instance,
                "license_expiry_date",
                None,
            ),
        )

        driver_status = attrs.get(
            "status",
            getattr(
                self.instance,
                "status",
                Driver.Status.AVAILABLE,
            ),
        )

        if (
            expiry_date
            and expiry_date < timezone.localdate()
            and driver_status == Driver.Status.AVAILABLE
        ):
            raise serializers.ValidationError(
                {
                    "status": (
                        "A driver with an expired licence "
                        "cannot be Available."
                    )
                }
            )

        return attrs