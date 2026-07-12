from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)

from .serializers import (
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    UserSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = serializer.validated_data["refresh"]

            token = RefreshToken(refresh_token)
            token.blacklist()

        except TokenError as error:
            raise serializers.ValidationError(
                {
                    "refresh": (
                        "The refresh token is invalid or already expired."
                    )
                }
            ) from error

        return Response(
            {
                "message": "Logout successful.",
            },
            status=status.HTTP_205_RESET_CONTENT,
        )