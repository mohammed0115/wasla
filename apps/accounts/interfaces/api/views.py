from __future__ import annotations

from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from apps.sms.domain.errors import SmsError

from apps.accounts.application.use_cases.complete_profile import (
    CompleteMerchantProfileCommand,
    CompleteMerchantProfileUseCase,
)
from apps.accounts.application.use_cases.login import LoginCommand, LoginUseCase
from apps.accounts.application.use_cases.request_hybrid_otp import (
    RequestHybridOtpCommand,
    RequestHybridOtpUseCase,
)
from apps.accounts.application.use_cases.resolve_auth_entry import (
    ResolveAuthEntryCommand,
    ResolveAuthEntryUseCase,
)
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
from apps.accounts.domain.auth_flow import AuthMethod
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep
from apps.accounts.interfaces.api.serializers import (
    AuthStartSerializer,
    CompleteProfileSerializer,
    LoginSerializer,
    MerchantRegisterSerializer,
    OtpLoginRequestSerializer,
    OtpLoginVerifySerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    SelectBusinessTypesSerializer,
    SelectCountrySerializer,
    CreateStoreSerializer,
)
from apps.accounts.services.audit_service import AccountAuditService
from apps.accounts.application.use_cases.select_country import SelectCountryCommand, SelectCountryUseCase
from apps.accounts.application.use_cases.select_business_types import (
    SelectBusinessTypesCommand,
    SelectBusinessTypesUseCase,
)
from apps.accounts.application.use_cases.create_store_from_onboarding import (
    CreateStoreFromOnboardingCommand,
    CreateStoreFromOnboardingUseCase,
)
from apps.accounts.models import AccountProfile, OnboardingProfile
from apps.accounts.application.use_cases.request_email_otp import RequestEmailOtpCommand, RequestEmailOtpUseCase
from apps.accounts.application.use_cases.verify_email_otp import VerifyEmailOtpCommand, VerifyEmailOtpUseCase
from apps.accounts.application.use_cases.request_login_otp import RequestLoginOtpCommand, RequestLoginOtpUseCase
from apps.accounts.application.use_cases.verify_login_otp import VerifyLoginOtpCommand, VerifyLoginOtpUseCase
from apps.accounts.application.use_cases.verify_hybrid_otp import (
    VerifyHybridOtpCommand,
    VerifyHybridOtpUseCase,
)


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
    if step == MerchantNextStep.COMPLETE_PROFILE:
        return reverse("auth:complete_profile")
    if step == MerchantNextStep.DASHBOARD:
        return reverse("web:dashboard")
    if step == MerchantNextStep.ONBOARDING_COUNTRY:
        return reverse("onboarding:country")
    if step == MerchantNextStep.ONBOARDING_BUSINESS_TYPES:
        return reverse("onboarding:business")
    if step == MerchantNextStep.STORE_CREATE:
        return reverse("web:dashboard_setup_store")
    return reverse("onboarding:country")


class AuthStartAPI(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = AuthStartSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        identifier = serializer.validated_data["identifier"]
        try:
            result = ResolveAuthEntryUseCase.execute(ResolveAuthEntryCommand(identifier=identifier))
        except AccountValidationError as exc:
            return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)

        prefill = {}
        if result.identifier_type.value == "email":
            prefill["email"] = result.identifier
        if result.identifier_type.value == "phone":
            prefill["phone"] = result.identifier

        if result.default_method == AuthMethod.OTP.value:
            next_step = reverse("api_auth_otp_request")
        elif result.default_method == AuthMethod.PASSWORD.value:
            next_step = reverse("api_auth_login")
        else:
            next_step = reverse("api_auth_register")

        return _success(
            data={
                "identifier": result.identifier,
                "identifier_type": result.identifier_type.value,
                "account_exists": result.account_exists,
                "available_methods": result.available_methods,
                "default_method": result.default_method,
                "can_register": result.can_register,
                "prefill": prefill,
                "social_providers": result.social_providers,
            },
            next_step=next_step,
        )


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


class CompleteProfileAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = CompleteProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            result = CompleteMerchantProfileUseCase.execute(
                CompleteMerchantProfileCommand(
                    user=request.user,
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

        next_step = _next_step_url(
            step=ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=request.user, otp_required=result.otp_required)
            ).step
        )
        return _success(
            data={"updated": True},
            next_step=next_step,
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

        next_step = reverse("onboarding:business")
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


class CreateStoreFromOnboardingAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "onboarding"

    def post(self, request):
        serializer = CreateStoreSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)
        try:
            result = CreateStoreFromOnboardingUseCase.execute(
                CreateStoreFromOnboardingCommand(
                    user=request.user,
                    name=serializer.validated_data["name"],
                    slug=serializer.validated_data["slug"],
                )
            )
        except AccountValidationError as exc:
            return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)

        next_step = reverse("web:dashboard")
        return _success(data={"tenant_id": result.tenant_id, "slug": result.slug}, next_step=next_step)


class OnboardingStatusAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "onboarding"

    def get(self, request):
        profile = OnboardingProfile.objects.filter(user=request.user).first()
        step = profile.step if profile else OnboardingProfile.STEP_REGISTERED
        return _success(data={"step": step}, next_step=_next_step_url(step=ResolveMerchantNextStepUseCase.execute(
            ResolveMerchantNextStepCommand(user=request.user, otp_required=False)
        ).step))


class OtpRequestAPI(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)
        identifier = (serializer.validated_data.get("identifier") or "").strip()
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        if identifier:
            try:
                result = RequestHybridOtpUseCase.execute(
                    RequestHybridOtpCommand(
                        identifier=identifier,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                )
            except SmsError as exc:
                return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)
            except AccountValidationError as exc:
                return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)
            except ValueError as exc:
                return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)
        else:
            if not request.user.is_authenticated:
                return _error(message="Authentication required.", http_status=status.HTTP_401_UNAUTHORIZED)
            try:
                result = RequestEmailOtpUseCase.execute(
                    RequestEmailOtpCommand(
                        user=request.user,
                        purpose=serializer.validated_data["purpose"],
                    )
                )
            except ValueError as exc:
                return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)

        next_step = reverse("auth:verify") if identifier else reverse("auth:otp_verify")
        data = {"otp_id": result.otp_id, "expires_at": str(result.expires_at)}
        if identifier:
            data["sent"] = bool(getattr(result, "sent", True))
            data["channel"] = getattr(result, "channel", "")
        return _success(data=data, next_step=next_step, http_status=status.HTTP_201_CREATED)


class OtpVerifyAPI(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return _error(message="Invalid input.", http_status=status.HTTP_400_BAD_REQUEST)

        identifier = (serializer.validated_data.get("identifier") or "").strip()

        if identifier:
            try:
                result = VerifyHybridOtpUseCase.execute(
                    VerifyHybridOtpCommand(
                        identifier=identifier,
                        code=serializer.validated_data["code"],
                    )
                )
            except AccountValidationError as exc:
                return _error(message=str(exc), field=getattr(exc, "field", None), http_status=status.HTTP_400_BAD_REQUEST)
            except ValueError as exc:
                return _error(message=str(exc), http_status=status.HTTP_400_BAD_REQUEST)
            profile = AccountProfile.objects.filter(user=result.user).first()
            otp_required = bool(profile and profile.email_verified_at is None and (getattr(result.user, "email", "") or "").strip())
            refresh = RefreshToken.for_user(result.user)
            next_step = _next_step_url(
                step=ResolveMerchantNextStepUseCase.execute(
                    ResolveMerchantNextStepCommand(user=result.user, otp_required=otp_required)
                ).step
            )
            return _success(
                data={
                    "user_id": result.user.id,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "created": bool(result.created),
                },
                next_step=next_step,
            )
        else:
            if not request.user.is_authenticated:
                return _error(message="Authentication required.", http_status=status.HTTP_401_UNAUTHORIZED)
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
