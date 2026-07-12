import csv
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from fleet.models import Vehicle

from .forms import (
    ExpenseForm,
    FuelLogForm,
    MaintenanceCloseForm,
    MaintenanceCreateForm,
    TripCompleteForm,
    TripForm,
)
from .models import Expense, FuelLog, MaintenanceRecord, Trip
from .services import (
    cancel_maintenance,
    cancel_trip,
    close_maintenance,
    complete_trip,
    dispatch_trip,
    open_maintenance,
)


TRIP_VIEW_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
    User.Role.DISPATCHER,
    User.Role.SAFETY_OFFICER,
    User.Role.FINANCIAL_ANALYST,
)

TRIP_MANAGE_ROLES = (
    User.Role.ADMIN,
    User.Role.DISPATCHER,
)

MAINTENANCE_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
)

FINANCE_VIEW_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
    User.Role.DISPATCHER,
    User.Role.FINANCIAL_ANALYST,
)

FINANCE_MANAGE_ROLES = (
    User.Role.ADMIN,
    User.Role.FINANCIAL_ANALYST,
)

FUEL_MANAGE_ROLES = (
    User.Role.ADMIN,
    User.Role.DISPATCHER,
    User.Role.FINANCIAL_ANALYST,
)



def apply_safe_sorting(queryset, requested_sort, allowed_sorts, default_sort):
    ordering = allowed_sorts.get(requested_sort, default_sort)
    return queryset.order_by(ordering)


def show_validation_errors(request, error):
    """Convert Django ValidationError messages into Django messages."""
    if hasattr(error, "message_dict"):
        for field_errors in error.message_dict.values():
            for error_message in field_errors:
                messages.error(request, error_message)
        return

    for error_message in error.messages:
        messages.error(request, error_message)


# ---------------------------------------------------------------------------
# Trip views
# ---------------------------------------------------------------------------

@role_required(*TRIP_VIEW_ROLES)
def trip_list(request):
    trips = (
        Trip.objects
        .select_related(
            "vehicle",
            "driver",
        )
        .all()
    )

    # ---------------------------------------------------------
    # Trip statistics
    # ---------------------------------------------------------
    trip_statistics = Trip.objects.aggregate(
        total=Count("id"),

        draft=Count(
            "id",
            filter=Q(
                status=Trip.Status.DRAFT
            ),
        ),

        dispatched=Count(
            "id",
            filter=Q(
                status=Trip.Status.DISPATCHED
            ),
        ),

        completed=Count(
            "id",
            filter=Q(
                status=Trip.Status.COMPLETED
            ),
        ),

        cancelled=Count(
            "id",
            filter=Q(
                status=Trip.Status.CANCELLED
            ),
        ),

        completed_revenue=Sum(
            "revenue",
            filter=Q(
                status=Trip.Status.COMPLETED
            ),
        ),
    )

    trip_statistics["completed_revenue"] = (
        trip_statistics["completed_revenue"]
        or Decimal("0")
    )

    # ---------------------------------------------------------
    # Search and filters
    # ---------------------------------------------------------
    search = request.GET.get(
        "search",
        "",
    ).strip()

    trip_status = request.GET.get(
        "status",
        "",
    ).strip()

    if search:
        trips = trips.filter(
            Q(source__icontains=search)
            | Q(destination__icontains=search)
            | Q(
                vehicle__registration_number__icontains=search
            )
            | Q(driver__name__icontains=search)
            | Q(notes__icontains=search)
        )

    if trip_status:
        trips = trips.filter(
            status=trip_status
        )

    # ---------------------------------------------------------
    # Sorting
    # ---------------------------------------------------------
    trip_sort = request.GET.get(
        "sort",
        "newest",
    )

    allowed_sorts = {
        "newest": "-created_at",
        "oldest": "created_at",
        "source": "source",
        "destination": "destination",
        "vehicle": "vehicle__registration_number",
        "driver": "driver__name",
        "status": "status",
        "cargo_high": "-cargo_weight",
        "distance_high": "-planned_distance",
        "revenue_high": "-revenue",
    }

    trips = trips.order_by(
        allowed_sorts.get(
            trip_sort,
            "-created_at",
        )
    )

    context = {
        "trips": trips,
        "trip_statistics": trip_statistics,
        "trip_statuses": Trip.Status.choices,
        "selected_sort": trip_sort,

        "can_manage": (
            request.user.is_superuser
            or request.user.role
            in TRIP_MANAGE_ROLES
        ),
    }

    return render(
        request,
        "operations/trip_list.html",
        context,
    )

@role_required(*TRIP_MANAGE_ROLES)
def trip_create(request):
    form = TripForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        trip = form.save(commit=False)
        trip.created_by = request.user
        trip.save()

        messages.success(
            request,
            f"Trip #{trip.pk} created as Draft.",
        )
        return redirect("operations:trip_detail", pk=trip.pk)

    return render(
        request,
        "operations/trip_form.html",
        {
            "form": form,
            "page_heading": "Create Trip",
            "button_text": "Create Draft Trip",
        },
    )


@role_required(*TRIP_MANAGE_ROLES)
def trip_update(request, pk):
    trip = get_object_or_404(Trip, pk=pk)

    if trip.status != Trip.Status.DRAFT:
        messages.error(request, "Only Draft trips can be edited.")
        return redirect("operations:trip_detail", pk=trip.pk)

    form = TripForm(request.POST or None, instance=trip)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Trip #{trip.pk} updated.")
        return redirect("operations:trip_detail", pk=trip.pk)

    return render(
        request,
        "operations/trip_form.html",
        {
            "form": form,
            "trip": trip,
            "page_heading": f"Update Trip #{trip.pk}",
            "button_text": "Update Trip",
        },
    )


@role_required(*TRIP_VIEW_ROLES)
def trip_detail(request, pk):
    trip = get_object_or_404(
        Trip.objects.select_related("vehicle", "driver", "created_by"),
        pk=pk,
    )

    complete_form = TripCompleteForm(
        trip=trip,
        initial={"final_odometer": trip.vehicle.odometer},
    )

    context = {
        "trip": trip,
        "complete_form": complete_form,
        "can_manage": (
            request.user.is_superuser
            or request.user.role in TRIP_MANAGE_ROLES
        ),
    }

    return render(request, "operations/trip_detail.html", context)


@require_POST
@role_required(*TRIP_MANAGE_ROLES)
def trip_dispatch(request, pk):
    trip = get_object_or_404(Trip, pk=pk)

    try:
        dispatch_trip(trip.pk)
        messages.success(
            request,
            f"Trip #{trip.pk} dispatched successfully.",
        )
    except ValidationError as error:
        show_validation_errors(request, error)

    return redirect("operations:trip_detail", pk=trip.pk)


@require_POST
@role_required(*TRIP_MANAGE_ROLES)
def trip_complete(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    form = TripCompleteForm(request.POST, trip=trip)

    if form.is_valid():
        try:
            complete_trip(
                trip.pk,
                form.cleaned_data["final_odometer"],
                form.cleaned_data["fuel_consumed"],
            )
            messages.success(request, f"Trip #{trip.pk} completed.")
        except ValidationError as error:
            show_validation_errors(request, error)
    else:
        for field_errors in form.errors.values():
            for error_message in field_errors:
                messages.error(request, error_message)

    return redirect("operations:trip_detail", pk=trip.pk)


@require_POST
@role_required(*TRIP_MANAGE_ROLES)
def trip_cancel(request, pk):
    trip = get_object_or_404(Trip, pk=pk)

    try:
        cancel_trip(trip.pk)
        messages.success(request, f"Trip #{trip.pk} cancelled.")
    except ValidationError as error:
        show_validation_errors(request, error)

    return redirect("operations:trip_detail", pk=trip.pk)


# ---------------------------------------------------------------------------
# Maintenance views
# ---------------------------------------------------------------------------

@role_required(*TRIP_VIEW_ROLES)
def maintenance_list(request):
    records = (
        MaintenanceRecord.objects
        .select_related("vehicle")
        .all()
    )

    status_value = request.GET.get("status", "").strip()
    search = request.GET.get("search", "").strip()

    if status_value:
        records = records.filter(status=status_value)

    if search:
        records = records.filter(
            Q(vehicle__registration_number__icontains=search)
            | Q(maintenance_type__icontains=search)
            | Q(description__icontains=search)
        )

    maintenance_sort = request.GET.get("sort", "newest")
    records = apply_safe_sorting(
        records,
        maintenance_sort,
        {
            "newest": "-created_at",
            "oldest": "created_at",
            "vehicle": "vehicle__registration_number",
            "priority": "priority",
            "status": "status",
            "cost_high": "-final_cost",
        },
        "-created_at",
    )

    return render(
        request,
        "operations/maintenance_list.html",
        {
            "records": records,
            "statuses": MaintenanceRecord.Status.choices,
            "can_manage": (
                request.user.is_superuser
                or request.user.role in MAINTENANCE_ROLES
            ),
        },
    )


@role_required(*MAINTENANCE_ROLES)
def maintenance_create(request):
    form = MaintenanceCreateForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            record = open_maintenance(
                vehicle=form.cleaned_data["vehicle"],
                maintenance_type=form.cleaned_data["maintenance_type"],
                description=form.cleaned_data["description"],
                priority=form.cleaned_data["priority"],
                estimated_cost=form.cleaned_data["estimated_cost"],
                expected_completion_date=form.cleaned_data[
                    "expected_completion_date"
                ],
                created_by=request.user,
            )

            messages.success(
                request,
                "Maintenance started. Vehicle is now In Shop.",
            )
            return redirect(
                "operations:maintenance_detail",
                pk=record.pk,
            )
        except ValidationError as error:
            show_validation_errors(request, error)

    return render(
        request,
        "operations/record_form.html",
        {
            "form": form,
            "page_heading": "Create Maintenance",
            "page_subtitle": (
                "Starting maintenance automatically moves the vehicle to In Shop."
            ),
            "button_text": "Start Maintenance",
            "cancel_url": "operations:maintenance_list",
        },
    )


@role_required(*TRIP_VIEW_ROLES)
def maintenance_detail(request, pk):
    record = get_object_or_404(
        MaintenanceRecord.objects.select_related("vehicle", "created_by"),
        pk=pk,
    )

    close_form = MaintenanceCloseForm(
        initial={"final_cost": record.estimated_cost}
    )

    return render(
        request,
        "operations/maintenance_detail.html",
        {
            "record": record,
            "close_form": close_form,
            "can_manage": (
                request.user.is_superuser
                or request.user.role in MAINTENANCE_ROLES
            ),
        },
    )


@require_POST
@role_required(*MAINTENANCE_ROLES)
def maintenance_close(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    form = MaintenanceCloseForm(request.POST)

    if form.is_valid():
        try:
            close_maintenance(
                record.pk,
                form.cleaned_data["final_cost"],
                form.cleaned_data["completion_notes"],
            )
            messages.success(
                request,
                "Maintenance completed. Vehicle is now Available.",
            )
        except ValidationError as error:
            show_validation_errors(request, error)
    else:
        for field_errors in form.errors.values():
            for error_message in field_errors:
                messages.error(request, error_message)

    return redirect("operations:maintenance_detail", pk=record.pk)


@require_POST
@role_required(*MAINTENANCE_ROLES)
def maintenance_cancel(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)

    try:
        cancel_maintenance(record.pk)
        messages.success(request, "Maintenance cancelled.")
    except ValidationError as error:
        show_validation_errors(request, error)

    return redirect("operations:maintenance_detail", pk=record.pk)


# ---------------------------------------------------------------------------
# Fuel log views
# ---------------------------------------------------------------------------

@role_required(*FINANCE_VIEW_ROLES)
def fuel_log_list(request):
    fuel_logs = (
        FuelLog.objects
        .select_related("vehicle", "trip")
        .all()
    )

    search = request.GET.get("search", "").strip()

    if search:
        fuel_logs = fuel_logs.filter(
            Q(vehicle__registration_number__icontains=search)
            | Q(trip__source__icontains=search)
            | Q(trip__destination__icontains=search)
        )

    fuel_sort = request.GET.get("sort", "newest")
    fuel_logs = apply_safe_sorting(
        fuel_logs,
        fuel_sort,
        {
            "newest": "-date",
            "oldest": "date",
            "vehicle": "vehicle__registration_number",
            "liters_high": "-liters",
            "cost_high": "-total_cost",
            "odometer_high": "-odometer",
        },
        "-date",
    )

    total_cost = (
        fuel_logs.aggregate(total=Sum("total_cost"))["total"]
        or Decimal("0")
    )

    return render(
        request,
        "operations/fuel_list.html",
        {
            "fuel_logs": fuel_logs,
            "total_cost": total_cost,
            "can_manage": (
                request.user.is_superuser
                or request.user.role in FUEL_MANAGE_ROLES
            ),
        },
    )


@role_required(*FUEL_MANAGE_ROLES)
def fuel_log_create(request):
    form = FuelLogForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        fuel_log = form.save(commit=False)
        fuel_log.created_by = request.user

        try:
            fuel_log.full_clean()
            fuel_log.save()
        except ValidationError as error:
            show_validation_errors(request, error)
        else:
            messages.success(request, "Fuel log created successfully.")
            return redirect("operations:fuel_log_list")

    return render(
        request,
        "operations/record_form.html",
        {
            "form": form,
            "page_heading": "Add Fuel Log",
            "page_subtitle": "Record fuel quantity, price and odometer.",
            "button_text": "Save Fuel Log",
            "cancel_url": "operations:fuel_log_list",
        },
    )


@role_required(*FUEL_MANAGE_ROLES)
def fuel_log_update(request, pk):
    fuel_log = get_object_or_404(FuelLog, pk=pk)
    form = FuelLogForm(request.POST or None, instance=fuel_log)

    if request.method == "POST" and form.is_valid():
        fuel_log = form.save(commit=False)

        try:
            fuel_log.full_clean()
            fuel_log.save()
        except ValidationError as error:
            show_validation_errors(request, error)
        else:
            messages.success(request, "Fuel log updated.")
            return redirect("operations:fuel_log_list")

    return render(
        request,
        "operations/record_form.html",
        {
            "form": form,
            "page_heading": "Update Fuel Log",
            "page_subtitle": "Update fuel information.",
            "button_text": "Update Fuel Log",
            "cancel_url": "operations:fuel_log_list",
        },
    )


@require_POST
@role_required(User.Role.ADMIN, User.Role.FINANCIAL_ANALYST)
def fuel_log_delete(request, pk):
    fuel_log = get_object_or_404(FuelLog, pk=pk)
    fuel_log.delete()

    messages.success(request, "Fuel log deleted.")
    return redirect("operations:fuel_log_list")


# ---------------------------------------------------------------------------
# Expense views
# ---------------------------------------------------------------------------

@role_required(*FINANCE_VIEW_ROLES)
def expense_list(request):
    expenses = (
        Expense.objects
        .select_related("vehicle", "trip")
        .all()
    )

    search = request.GET.get("search", "").strip()
    expense_type = request.GET.get("expense_type", "").strip()

    if search:
        expenses = expenses.filter(
            Q(vehicle__registration_number__icontains=search)
            | Q(description__icontains=search)
        )

    if expense_type:
        expenses = expenses.filter(expense_type=expense_type)

    expense_sort = request.GET.get("sort", "newest")
    expenses = apply_safe_sorting(
        expenses,
        expense_sort,
        {
            "newest": "-date",
            "oldest": "date",
            "vehicle": "vehicle__registration_number",
            "type": "expense_type",
            "amount_high": "-amount",
            "amount_low": "amount",
        },
        "-date",
    )

    total_amount = (
        expenses.aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )

    return render(
        request,
        "operations/expense_list.html",
        {
            "expenses": expenses,
            "expense_types": Expense.ExpenseType.choices,
            "total_amount": total_amount,
            "can_manage": (
                request.user.is_superuser
                or request.user.role in FINANCE_MANAGE_ROLES
            ),
        },
    )


@role_required(*FINANCE_MANAGE_ROLES)
def expense_create(request):
    form = ExpenseForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.created_by = request.user

        try:
            expense.full_clean()
            expense.save()
        except ValidationError as error:
            show_validation_errors(request, error)
        else:
            messages.success(request, "Expense created successfully.")
            return redirect("operations:expense_list")

    return render(
        request,
        "operations/record_form.html",
        {
            "form": form,
            "page_heading": "Add Expense",
            "page_subtitle": (
                "Record tolls, parking, repairs and other operational expenses."
            ),
            "button_text": "Save Expense",
            "cancel_url": "operations:expense_list",
        },
    )


@role_required(*FINANCE_MANAGE_ROLES)
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    form = ExpenseForm(request.POST or None, instance=expense)

    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)

        try:
            expense.full_clean()
            expense.save()
        except ValidationError as error:
            show_validation_errors(request, error)
        else:
            messages.success(request, "Expense updated.")
            return redirect("operations:expense_list")

    return render(
        request,
        "operations/record_form.html",
        {
            "form": form,
            "page_heading": "Update Expense",
            "page_subtitle": "Update expense information.",
            "button_text": "Update Expense",
            "cancel_url": "operations:expense_list",
        },
    )


@require_POST
@role_required(*FINANCE_MANAGE_ROLES)
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    expense.delete()

    messages.success(request, "Expense deleted.")
    return redirect("operations:expense_list")


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def build_vehicle_report_rows():
    """
    Build vehicle-level performance rows.

    Required PDF formulas:
      Operational Cost = Fuel Cost + Maintenance Cost
      ROI = (Revenue - Operational Cost) / Acquisition Cost * 100

    Other expenses are shown separately and are included in Net Profit.
    """
    rows = []

    for vehicle in Vehicle.objects.all():
        completed_trips = list(
            vehicle.trips.filter(status=Trip.Status.COMPLETED)
        )

        revenue = sum(
            (trip.revenue for trip in completed_trips),
            Decimal("0"),
        )

        fuel_totals = vehicle.fuel_logs.aggregate(
            cost=Sum("total_cost"),
            liters=Sum("liters"),
        )
        fuel_cost = fuel_totals["cost"] or Decimal("0")
        fuel_liters = fuel_totals["liters"] or Decimal("0")

        maintenance_cost = (
            vehicle.maintenance_records
            .filter(status=MaintenanceRecord.Status.COMPLETED)
            .aggregate(total=Sum("final_cost"))["total"]
            or Decimal("0")
        )

        other_expenses = (
            vehicle.expenses.aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )

        # Exact formula required by the TransitOps problem statement.
        required_operational_cost = fuel_cost + maintenance_cost

        # Extended total shown separately for a fuller business calculation.
        total_cost_with_other_expenses = (
            required_operational_cost + other_expenses
        )

        # Net profit after every recorded cost.
        profit = revenue - total_cost_with_other_expenses

        total_distance = Decimal("0")
        for trip in completed_trips:
            if (
                trip.start_odometer is not None
                and trip.final_odometer is not None
            ):
                total_distance += (
                    trip.final_odometer - trip.start_odometer
                )

        fuel_efficiency = Decimal("0")
        if fuel_liters > 0:
            fuel_efficiency = total_distance / fuel_liters

        # Exact ROI formula required by the PDF.
        roi = Decimal("0")
        if vehicle.acquisition_cost > 0:
            roi = (
                (
                    revenue - required_operational_cost
                )
                / vehicle.acquisition_cost
                * Decimal("100")
            )

        rows.append(
            {
                "vehicle": vehicle,
                "completed_trips": len(completed_trips),
                "total_distance": total_distance,
                "fuel_liters": fuel_liters,
                "fuel_efficiency": fuel_efficiency,
                "revenue": revenue,
                "fuel_cost": fuel_cost,
                "maintenance_cost": maintenance_cost,
                "other_expenses": other_expenses,
                "operational_cost": required_operational_cost,
                "total_cost_with_other_expenses": (
                    total_cost_with_other_expenses
                ),
                "profit": profit,
                "roi": roi,
            }
        )

    return rows


@role_required(*TRIP_VIEW_ROLES)
def reports_dashboard(request):
    rows = build_vehicle_report_rows()

    totals = {
        "revenue": sum(
            (row["revenue"] for row in rows),
            Decimal("0"),
        ),
        "fuel_cost": sum(
            (row["fuel_cost"] for row in rows),
            Decimal("0"),
        ),
        "maintenance_cost": sum(
            (row["maintenance_cost"] for row in rows),
            Decimal("0"),
        ),
        "other_expenses": sum(
            (row["other_expenses"] for row in rows),
            Decimal("0"),
        ),
        "operational_cost": sum(
            (row["operational_cost"] for row in rows),
            Decimal("0"),
        ),
        "total_cost_with_other_expenses": sum(
            (
                row["total_cost_with_other_expenses"]
                for row in rows
            ),
            Decimal("0"),
        ),
        "profit": sum(
            (row["profit"] for row in rows),
            Decimal("0"),
        ),
    }

    return render(
        request,
        "operations/reports.html",
        {
            "rows": rows,
            "totals": totals,
        },
    )


@role_required(*TRIP_VIEW_ROLES)
def export_vehicle_report_csv(request):
    rows = build_vehicle_report_rows()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="transitops_vehicle_report.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Registration Number",
            "Vehicle",
            "Status",
            "Completed Trips",
            "Distance KM",
            "Fuel Litres",
            "Fuel Efficiency KM/L",
            "Revenue",
            "Fuel Cost",
            "Maintenance Cost",
            "Other Expenses",
            "Required Operational Cost",
            "Total Cost Including Other Expenses",
            "Net Profit",
            "ROI Percentage",
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row["vehicle"].registration_number,
                row["vehicle"].vehicle_name,
                row["vehicle"].get_status_display(),
                row["completed_trips"],
                round(row["total_distance"], 2),
                round(row["fuel_liters"], 2),
                round(row["fuel_efficiency"], 2),
                round(row["revenue"], 2),
                round(row["fuel_cost"], 2),
                round(row["maintenance_cost"], 2),
                round(row["other_expenses"], 2),
                round(row["operational_cost"], 2),
                round(row["total_cost_with_other_expenses"], 2),
                round(row["profit"], 2),
                round(row["roi"], 2),
            ]
        )

    return response


@role_required(*TRIP_VIEW_ROLES)
def export_vehicle_report_pdf(request):
    rows = build_vehicle_report_rows()
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="TransitOps Vehicle Performance Report",
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph("TransitOps Vehicle Performance Report", styles["Title"]),
        Paragraph(
            f"Generated: {timezone.localtime():%d %b %Y, %I:%M %p}",
            styles["Normal"],
        ),
        Spacer(1, 8),
    ]

    table_data = [
        [
            "Registration",
            "Vehicle",
            "Trips",
            "Distance",
            "Efficiency",
            "Revenue",
            "Operational Cost",
            "Net Profit",
            "ROI",
        ]
    ]

    for row in rows:
        table_data.append(
            [
                row["vehicle"].registration_number,
                row["vehicle"].vehicle_name,
                str(row["completed_trips"]),
                f'{row["total_distance"]:.2f} km',
                f'{row["fuel_efficiency"]:.2f} km/L',
                f'INR {row["revenue"]:.2f}',
                f'INR {row["operational_cost"]:.2f}',
                f'INR {row["profit"]:.2f}',
                f'{row["roi"]:.2f}%',
            ]
        )

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            28 * mm,
            32 * mm,
            14 * mm,
            22 * mm,
            24 * mm,
            25 * mm,
            32 * mm,
            26 * mm,
            18 * mm,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4f99")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d5dd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(table)

    document.build(elements)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        'attachment; filename="transitops_vehicle_report.pdf"'
    )
    return response
