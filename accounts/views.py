from django.contrib import messages
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from accounts.decorators import role_required

from .forms import (
    FrontendUserCreateForm,
    FrontendUserUpdateForm,
)
from .models import User


ACCOUNT_MANAGE_ROLES = (
    User.Role.ADMIN,
)


@role_required(*ACCOUNT_MANAGE_ROLES)
def account_list(request):
    users = User.objects.all().order_by(
        "first_name",
        "last_name",
        "email",
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    selected_role = request.GET.get(
        "role",
        "",
    ).strip()

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    if search:
        users = users.filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    if selected_role:
        users = users.filter(
            role=selected_role
        )

    if selected_status == "active":
        users = users.filter(
            is_active=True
        )

    elif selected_status == "inactive":
        users = users.filter(
            is_active=False
        )

    context = {
        "users": users,
        "roles": User.Role.choices,
        "selected_role": selected_role,
        "selected_status": selected_status,
        "search": search,
    }

    return render(
        request,
        "accounts/account_list.html",
        context,
    )


@role_required(*ACCOUNT_MANAGE_ROLES)
def account_create(request):
    form = FrontendUserCreateForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        user_account = form.save()

        messages.success(
            request,
            (
                f"Account {user_account.email} "
                "created successfully."
            ),
        )

        return redirect(
            "accounts:account_list"
        )

    return render(
        request,
        "accounts/account_form.html",
        {
            "form": form,
            "page_heading": "Add Account",
            "page_subtitle": (
                "Create a TransitOps user and assign a role."
            ),
            "button_text": "Create Account",
            "is_edit": False,
        },
    )


@role_required(*ACCOUNT_MANAGE_ROLES)
def account_update(request, pk):
    user_account = get_object_or_404(
        User,
        pk=pk,
    )

    form = FrontendUserUpdateForm(
        request.POST or None,
        instance=user_account,
    )

    if request.method == "POST" and form.is_valid():
        # The currently logged-in admin must not disable
        # their own account.
        if (
            user_account.pk == request.user.pk
            and form.cleaned_data.get("is_active") is False
        ):
            form.add_error(
                "is_active",
                "You cannot deactivate your own account.",
            )

        else:
            updated_account = form.save()

            messages.success(
                request,
                (
                    f"Account {updated_account.email} "
                    "updated successfully."
                ),
            )

            return redirect(
                "accounts:account_list"
            )

    return render(
        request,
        "accounts/account_form.html",
        {
            "form": form,
            "user_account": user_account,
            "page_heading": "Edit Account",
            "page_subtitle": (
                f"Update the account for "
                f"{user_account.email}."
            ),
            "button_text": "Save Changes",
            "is_edit": True,
        },
    )


@require_POST
@role_required(*ACCOUNT_MANAGE_ROLES)
def account_delete(request, pk):
    user_account = get_object_or_404(
        User,
        pk=pk,
    )

    if user_account.pk == request.user.pk:
        messages.error(
            request,
            "You cannot delete your own account.",
        )

        return redirect(
            "accounts:account_list"
        )

    if user_account.is_superuser:
        messages.error(
            request,
            "A superuser account cannot be deleted here.",
        )

        return redirect(
            "accounts:account_list"
        )

    email = user_account.email

    user_account.delete()

    messages.success(
        request,
        f"Account {email} deleted successfully.",
    )

    return redirect(
        "accounts:account_list"
    )