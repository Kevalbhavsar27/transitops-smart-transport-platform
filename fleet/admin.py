from django.contrib import admin

from .models import Driver, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        "registration_number",
        "vehicle_name",
        "vehicle_type",
        "maximum_load_capacity",
        "odometer",
        "region",
        "status",
    ]

    list_filter = [
        "vehicle_type",
        "status",
        "region",
    ]

    search_fields = [
        "registration_number",
        "vehicle_name",
        "model",
    ]


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "license_number",
        "license_category",
        "license_expiry_date",
        "safety_score",
        "status",
    ]

    list_filter = [
        "status",
        "license_category",
    ]

    search_fields = [
        "name",
        "license_number",
        "contact_number",
    ]