from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from fleet.models import Vehicle


MAX_DOCUMENT_SIZE = 5 * 1024 * 1024


def validate_document_size(uploaded_file):
    if uploaded_file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError("Document size cannot exceed 5 MB.")


def vehicle_document_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return (
        f"vehicle_documents/{instance.vehicle_id}/"
        f"{uuid4().hex}{suffix}"
    )


class VehicleDocument(models.Model):
    class DocumentType(models.TextChoices):
        REGISTRATION = "REGISTRATION", "Registration Certificate"
        INSURANCE = "INSURANCE", "Insurance"
        PERMIT = "PERMIT", "Permit"
        PUC = "PUC", "Pollution Certificate"
        FITNESS = "FITNESS", "Fitness Certificate"
        OTHER = "OTHER", "Other"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    title = models.CharField(max_length=150)
    reference_number = models.CharField(
        max_length=100,
        blank=True,
    )
    file = models.FileField(
        upload_to=vehicle_document_upload_to,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "jpg", "jpeg", "png"]
            ),
            validate_document_size,
        ],
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_vehicle_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["vehicle__registration_number", "document_type", "title"]
        indexes = [
            models.Index(fields=["document_type"]),
            models.Index(fields=["expiry_date"]),
        ]

    def clean(self):
        errors = {}
        if (
            self.issue_date
            and self.expiry_date
            and self.expiry_date < self.issue_date
        ):
            errors["expiry_date"] = (
                "Expiry date cannot be earlier than issue date."
            )
        if errors:
            raise ValidationError(errors)

    @property
    def is_expired(self):
        return bool(
            self.expiry_date
            and self.expiry_date < timezone.localdate()
        )

    def __str__(self):
        return (
            f"{self.vehicle.registration_number} - "
            f"{self.title}"
        )
