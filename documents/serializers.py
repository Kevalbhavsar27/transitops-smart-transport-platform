from rest_framework import serializers

from .models import VehicleDocument


class VehicleDocumentSerializer(serializers.ModelSerializer):
    vehicle_registration = serializers.CharField(
        source="vehicle.registration_number",
        read_only=True,
    )
    document_type_display = serializers.CharField(
        source="get_document_type_display",
        read_only=True,
    )
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = VehicleDocument
        fields = [
            "id",
            "vehicle",
            "vehicle_registration",
            "document_type",
            "document_type_display",
            "title",
            "reference_number",
            "file",
            "issue_date",
            "expiry_date",
            "is_expired",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "is_expired",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        issue_date = attrs.get(
            "issue_date",
            getattr(self.instance, "issue_date", None),
        )
        expiry_date = attrs.get(
            "expiry_date",
            getattr(self.instance, "expiry_date", None),
        )
        if issue_date and expiry_date and expiry_date < issue_date:
            raise serializers.ValidationError(
                {"expiry_date": "Expiry date cannot precede issue date."}
            )
        return attrs
