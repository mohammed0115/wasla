from __future__ import annotations

from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.application.use_cases.login import LoginCommand, LoginUseCase
from apps.accounts.application.use_cases.resolve_merchant_next_step import (
    ResolveMerchantNextStepCommand,
    ResolveMerchantNextStepUseCase,
)
from apps.accounts.application.use_cases.register_merchant import (
    RegisterMerchantCommand,
    RegisterMerchantUseCase,
)
from apps.accounts.domain.errors import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    AccountValidationError,
    InvalidCredentialsError,
)
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep
from apps.accounts.interfaces.api.serializers import (
    LoginSerializer,
    MerchantRegisterSerializer,
    OtpLoginRequestSerializer,
    OtpLoginVerifySerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    SelectBusinessTypesSerializer,
    SelectCountrySerializer,
)
from apps.accounts.services.audit_service import AccountAuditService
from apps.accounts.application.use_cases.select_country import SelectCountryCommand, SelectCountryUseCase
from apps.accounts.application.use_cases.select_business_types import (
    SelectBusinessTypesCommand,
    SelectBusinessTypesUseCase,
)
from apps.accounts.application.use_cases.request_email_otp import RequestEmailOtpCommand, RequestEmailOtpUseCase
from apps.accounts.application.use_cases.verify_email_otp import VerifyEmailOtpCommand, VerifyEmailOtpUseCase
from apps.accounts.application.use_cases.request_login_otp import RequestLoginOtpCommand, RequestLoginOtpUseCase
from apps.accounts.application.use_cases.verify_login_otp import VerifyLoginOtpCommand, VerifyLoginOtpUseCase


def _client_ip(request) -> str | None:
    value = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
    if not value:
        return None
    return value.split(",")[0].strip() or None


def _success(*, data: dict, next_step: str, http_status: int = status.HTTP_200_OK) -> Response:
    return Response({"success": True, "data": data, "next_step": next_step}, status=http_status)


def _error(*, message: str, field: str | None = None, http_status: int = 400) -> Response:
    payload: dict = {"success": False, "data": {}, "next_step": "", "error": {"message": message}}
    if field:
        payload["error"]["field"] = field
    return Response(payload, status=http_status)


def _next_step_url(*, step: MerchantNextStep) -> str:
    if step == MerchantNextStep.OTP_VERIFY:
        return reverse("auth:otp_verify")
    if step == MerchantNextStep.DASHBOARD:
        return reverse("web:dashboard")
    if step == MerchantNextStep.ONBOARDING_COUNTRY:
        return reverse("onboarding:country")
    if step == MerchantNextStep.ONBOARDING_BUSINESS_TYPES:
        return reverse("onboarding:business_types")
    if step == MerchantNextStep.STORE_CREATE:
        return reverse("web:dashboard_setup_store")
    return reverse("onboarding:country")


class RegisterMerchantAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = MerchantRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            result = RegisterMerchantUseCase.execute(
                RegisterMerchantCommand(
                    full_name=data["full_name"],
                    phone=data["phone"],
                    email=data["email"],
                    password=data["password"],
                    accept_terms=bool(data["accept_terms"]),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except AccountAlreadyExistsError as exc:
            return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_409_CONFLICT)
        except AccountValidationError as exc:
            return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(result.user)
        next_step = _next_step_url(
            step=ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=result.user, otp_required=result.otp_required)
            ).step
        )
        return _success(
            data={
                "user_id": result.user.id,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            next_step=next_step,
            http_status=status.HTTP_201_CREATED,
        )


class LoginAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        identifier = serializer.validated_data["identifier"]

        try:
            result = LoginUseCase.execute(
                LoginCommand(
                    identifier=identifier,
                    password=serializer.validated_data["password"],
                )
            )
        except InvalidCredentialsError as exc:
            AccountAuditService.record_action(
                user=None,
                action=AccountAuditService.ACTION_LOGIN_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"identifier": identifier},
            )
            return _error(message=str(exc), http_status=status.HTTP_401_UNAUTHORIZED)

        AccountAuditService.record_action(
            user=result.user,
            action=AccountAuditService.ACTION_LOGIN_SUCCEEDED,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={},
        )

        refresh = RefreshToken.for_user(result.user)
        next_step = _next_step_url(
            step=ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=result.user, otp_required=result.otp_required)
            ).step
        )
        return _success(
            data={
                "user_id": result.user.id,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            next_step=next_step,
        )


class SelectCountryAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "onboarding"

    def post(self, request):
        serializer = SelectCountrySerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        try:
            result = SelectCountryUseCase.execute(
                SelectCountryCommand(
                    user=request.user,
                    country=serializer.validated_data["country"],
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except AccountValidationError as exc:
            return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)

        next_step = reverse("onboarding:business_types")
        return _success(data={"country": result.country}, next_step=next_step)


class SelectBusinessTypesAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "onboarding"

    def post(self, request):
        serializer = SelectBusinessTypesSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        try:
            result = SelectBusinessTypesUseCase.execute(
                SelectBusinessTypesCommand(
                    user=request.user,
                    business_types=list(serializer.validated_data["business_types"]),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except AccountValidationError as exc:
            return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)

        next_step = reverse("web:dashboard_setup_store")
        return _success(data={"business_types": result.business_types}, next_step=next_step)


class OtpRequestAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)
        try:
            result = RequestEmailOtpUseCase.execute(
                RequestEmailOtpCommand(
                    user=request.user,
                    purpose=serializer.validated_data["purpose"],
                )
            )
        except ValueError as exc:
            return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)

        return _success(
            data={"otp_id": result.otp_id, "expires_at": str(result.expires_at)},
            next_step=reverse("auth:otp_verify"),
            http_status=status.HTTP_201_CREATED,
        )


class OtpVerifyAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        try:
            _ = VerifyEmailOtpUseCase.execute(
                VerifyEmailOtpCommand(
                    user=request.user,
                    purpose=serializer.validated_data["purpose"],
                    code=serializer.validated_data["code"],
                )
            )
        except ValueError as exc:
            return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)

        next_step = _next_step_url(
            step=ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=request.user, otp_required=False)
            ).step
        )
        return _success(data={"verified": True}, next_step=next_step)


class OtpLoginRequestAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = OtpLoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)
        identifier = serializer.validated_data["identifier"]

        try:
            result = RequestLoginOtpUseCase.execute(RequestLoginOtpCommand(identifier=identifier))
        except AccountNotFoundError as exc:
            return _error(message=str(exc), http_status=status.HTTP_404_NOT_FOUND)
        except AccountValidationError as exc:
            return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)

        return _success(
            data={"otp_id": result.otp_id, "expires_at": str(result.expires_at)},
            next_step=reverse("api_auth_otp_login_verify"),
            http_status=status.HTTP_201_CREATED,
        )


class OtpLoginVerifyAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = OtpLoginVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        identifier = serializer.validated_data["identifier"]

        try:
            result = VerifyLoginOtpUseCase.execute(
                VerifyLoginOtpCommand(identifier=identifier, code=serializer.validated_data["code"])
            )
        except AccountNotFoundError as exc:
            AccountAuditService.record_action(
                user=None,
                action=AccountAuditService.ACTION_LOGIN_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"identifier": identifier},
            )
            return _error(message=str(exc), http_status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            AccountAuditService.record_action(
                user=None,
                action=AccountAuditService.ACTION_LOGIN_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"identifier": identifier},
            )
            return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)

        AccountAuditService.record_action(
            user=result.user,
            action=AccountAuditService.ACTION_LOGIN_SUCCEEDED,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"method": "otp"},
        )

        refresh = RefreshToken.for_user(result.user)
        next_step = _next_step_url(
            step=ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=result.user, otp_required=False)
            ).step
        )
        return _success(
            data={"user_id": result.user.id, "access": str(refresh.access_token), "refresh": str(refresh)},
            next_step=next_step,
        )
