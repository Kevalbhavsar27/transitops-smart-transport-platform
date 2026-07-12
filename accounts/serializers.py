from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)

from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_display",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "email",
            "role",
            "is_active",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


class CustomTokenObtainPairSerializer(
    TokenObtainPairSerializer
):
    """
    Adds role and email information to JWT claims
    and returns user data with login response.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = (
            user.get_full_name() or user.email
        )

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_active:
            raise serializers.ValidationError(
                "This account is inactive."
            )

        data["user"] = UserSerializer(self.user).data

        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        trim_whitespace=True,
    )