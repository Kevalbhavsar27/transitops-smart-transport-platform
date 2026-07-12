from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager because email is used instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        FLEET_MANAGER = "FLEET_MANAGER", "Fleet Manager"
        DISPATCHER = "DISPATCHER", "Dispatcher"
        SAFETY_OFFICER = "SAFETY_OFFICER", "Safety Officer"
        FINANCIAL_ANALYST = "FINANCIAL_ANALYST", "Financial Analyst"

    username = None

    email = models.EmailField(
        unique=True,
        help_text="Used for login.",
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.DISPATCHER,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["first_name", "last_name", "email"]

    def __str__(self):
        return self.get_full_name() or self.email