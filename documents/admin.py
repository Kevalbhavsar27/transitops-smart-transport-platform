from django.contrib import admin

from .models import VehicleDocument


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "vehicle",
        "document_type",
        "title",
        "reference_number",
        "expiry_date",
        "uploaded_by",
    ]
    list_filter = ["document_type", "expiry_date"]
    search_fields = [
        "vehicle__registration_number",
        "title",
        "reference_number",
    ]
