from pathlib import Path

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms import VehicleDocumentForm
from .models import VehicleDocument


DOCUMENT_VIEW_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
    User.Role.DISPATCHER,
    User.Role.SAFETY_OFFICER,
    User.Role.FINANCIAL_ANALYST,
)

DOCUMENT_MANAGE_ROLES = (
    User.Role.ADMIN,
    User.Role.FLEET_MANAGER,
    User.Role.SAFETY_OFFICER,
)


def safe_sort(queryset, requested, allowed, default):
    return queryset.order_by(allowed.get(requested, default))


@role_required(*DOCUMENT_VIEW_ROLES)
def document_list(request):
    documents = VehicleDocument.objects.select_related(
        "vehicle",
        "uploaded_by",
    )

    search = request.GET.get("search", "").strip()
    vehicle_id = request.GET.get("vehicle", "").strip()
    document_type = request.GET.get("document_type", "").strip()
    sort = request.GET.get("sort", "vehicle")

    if search:
        documents = documents.filter(title__icontains=search)
    if vehicle_id:
        documents = documents.filter(vehicle_id=vehicle_id)
    if document_type:
        documents = documents.filter(document_type=document_type)

    documents = safe_sort(
        documents,
        sort,
        {
            "vehicle": "vehicle__registration_number",
            "title": "title",
            "type": "document_type",
            "expiry": "expiry_date",
            "newest": "-created_at",
        },
        "vehicle__registration_number",
    )

    return render(
        request,
        "documents/document_list.html",
        {
            "documents": documents,
            "document_types": VehicleDocument.DocumentType.choices,
            "can_manage": (
                request.user.is_superuser
                or request.user.role in DOCUMENT_MANAGE_ROLES
            ),
        },
    )


@role_required(*DOCUMENT_MANAGE_ROLES)
def document_create(request):
    form = VehicleDocumentForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.uploaded_by = request.user
        document.full_clean()
        document.save()
        messages.success(request, "Vehicle document uploaded.")
        return redirect("documents:document_list")

    return render(
        request,
        "documents/document_form.html",
        {"form": form},
    )


@role_required(*DOCUMENT_VIEW_ROLES)
def document_download(request, pk):
    document = get_object_or_404(VehicleDocument, pk=pk)

    try:
        file_handle = document.file.open("rb")
    except (FileNotFoundError, ValueError) as error:
        raise Http404("Document file was not found.") from error

    filename = Path(document.file.name).name
    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=filename,
    )


@require_POST
@role_required(*DOCUMENT_MANAGE_ROLES)
def document_delete(request, pk):
    document = get_object_or_404(VehicleDocument, pk=pk)
    stored_file = document.file
    document.delete()
    stored_file.delete(save=False)
    messages.success(request, "Vehicle document deleted.")
    return redirect("documents:document_list")
