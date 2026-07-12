from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import User

from .forms import DriverForm, VehicleForm
from .models import Driver, Vehicle


VEHICLE_VIEW_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
    User.Role.DISPATCHER,
    User.Role.SAFETY_OFFICER,
    User.Role.FINANCIAL_ANALYST,
)

VEHICLE_MANAGE_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
)

DRIVER_VIEW_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
    User.Role.DISPATCHER,
    User.Role.SAFETY_OFFICER,
    User.Role.FINANCIAL_ANALYST,
)

DRIVER_MANAGE_ROLES = (
    User.Role.ADMIN,
    User.Role.DISPATCHER,
    User.Role.SAFETY_OFFICER,
)


@role_required(*VEHICLE_VIEW_ROLES)
def vehicle_list(request):
    vehicles = Vehicle.objects.all()

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    vehicle_type = request.GET.get("vehicle_type", "").strip()
    region = request.GET.get("region", "").strip()

    if search:
        vehicles = vehicles.filter(
            Q(registration_number__icontains=search)
            | Q(vehicle_name__icontains=search)
            | Q(model__icontains=search)
        )

    if status:
        vehicles = vehicles.filter(status=status)

    if vehicle_type:
        vehicles = vehicles.filter(vehicle_type=vehicle_type)

    if region:
        vehicles = vehicles.filter(region__icontains=region)

    context = {
        "vehicles": vehicles,
        "vehicle_statuses": Vehicle.Status.choices,
        "vehicle_types": Vehicle.VehicleType.choices,
        "can_manage": (
            request.user.is_superuser
            or request.user.role in VEHICLE_MANAGE_ROLES
        ),
    }

    return render(
        request,
        "fleet/vehicle_list.html",
        context,
    )


@role_required(*VEHICLE_MANAGE_ROLES)
def vehicle_create(request):
    form = VehicleForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        vehicle = form.save()

        messages.success(
            request,
            f"Vehicle {vehicle.registration_number} created successfully.",
        )

        return redirect("fleet:vehicle_list")

    return render(
        request,
        "fleet/vehicle_form.html",
        {
            "form": form,
            "page_heading": "Register Vehicle",
            "button_text": "Save Vehicle",
        },
    )


@role_required(*VEHICLE_MANAGE_ROLES)
def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)

    form = VehicleForm(
        request.POST or None,
        instance=vehicle,
    )

    if request.method == "POST" and form.is_valid():
        vehicle = form.save()

        messages.success(
            request,
            f"Vehicle {vehicle.registration_number} updated successfully.",
        )

        return redirect("fleet:vehicle_list")

    return render(
        request,
        "fleet/vehicle_form.html",
        {
            "form": form,
            "vehicle": vehicle,
            "page_heading": "Update Vehicle",
            "button_text": "Update Vehicle",
        },
    )


@role_required(User.Role.ADMIN)
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)

    if request.method == "POST":
        registration_number = vehicle.registration_number
        vehicle.delete()

        messages.success(
            request,
            f"Vehicle {registration_number} deleted.",
        )

        return redirect("fleet:vehicle_list")

    return render(
        request,
        "fleet/confirm_delete.html",
        {
            "object": vehicle,
            "object_type": "vehicle",
            "cancel_url": "fleet:vehicle_list",
        },
    )


@role_required(*DRIVER_VIEW_ROLES)
def driver_list(request):
    drivers = Driver.objects.all()

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    license_category = request.GET.get(
        "license_category",
        "",
    ).strip()

    if search:
        drivers = drivers.filter(
            Q(name__icontains=search)
            | Q(license_number__icontains=search)
            | Q(contact_number__icontains=search)
        )

    if status:
        drivers = drivers.filter(status=status)

    if license_category:
        drivers = drivers.filter(
            license_category__icontains=license_category
        )

    context = {
        "drivers": drivers,
        "driver_statuses": Driver.Status.choices,
        "can_manage": (
            request.user.is_superuser
            or request.user.role in DRIVER_MANAGE_ROLES
        ),
    }

    return render(
        request,
        "fleet/driver_list.html",
        context,
    )


@role_required(*DRIVER_MANAGE_ROLES)
def driver_create(request):
    form = DriverForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        driver = form.save()

        messages.success(
            request,
            f"Driver {driver.name} created successfully.",
        )

        return redirect("fleet:driver_list")

    return render(
        request,
        "fleet/driver_form.html",
        {
            "form": form,
            "page_heading": "Register Driver",
            "button_text": "Save Driver",
        },
    )


@role_required(*DRIVER_MANAGE_ROLES)
def driver_update(request, pk):
    driver = get_object_or_404(Driver, pk=pk)

    form = DriverForm(
        request.POST or None,
        instance=driver,
    )

    if request.method == "POST" and form.is_valid():
        driver = form.save()

        messages.success(
            request,
            f"Driver {driver.name} updated successfully.",
        )

        return redirect("fleet:driver_list")

    return render(
        request,
        "fleet/driver_form.html",
        {
            "form": form,
            "driver": driver,
            "page_heading": "Update Driver",
            "button_text": "Update Driver",
        },
    )


@role_required(User.Role.ADMIN, User.Role.SAFETY_OFFICER)
def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)

    if request.method == "POST":
        driver_name = driver.name
        driver.delete()

        messages.success(
            request,
            f"Driver {driver_name} deleted.",
        )

        return redirect("fleet:driver_list")

    return render(
        request,
        "fleet/confirm_delete.html",
        {
            "object": driver,
            "object_type": "driver",
            "cancel_url": "fleet:driver_list",
        },
    )