from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.decorators import role_required

from .forms import FrontendUserCreateForm
from .models import User
from django.db.models import Q

ACCOUNT_MANAGE_ROLES = (
    User.Role.ADMIN,
)


@role_required(*ACCOUNT_MANAGE_ROLES)
def account_list(request):
    users = User.objects.all().order_by(
        "first_name",
        "email",
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    role = request.GET.get(
        "role",
        "",
    ).strip()

    if search:
        users = users.filter(
          Q(email__icontains=search)
        | Q(first_name__icontains=search)
        | Q(last_name__icontains=search)
    )

    if role:
        users = users.filter(
            role=role
        )

    context = {
        "users": users,
        "roles": User.Role.choices,
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
        user = form.save()

        messages.success(
            request,
            f"Account for {user.email} created successfully.",
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
        },
    )