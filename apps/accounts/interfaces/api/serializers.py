from __future__ import annotations

from rest_framework import serializers


class MerchantRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=8, write_only=True)
    accept_terms = serializers.BooleanField()


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True)


class AuthStartSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)


class CompleteProfileSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=8, write_only=True)
    accept_terms = serializers.BooleanField()


class SelectCountrySerializer(serializers.Serializer):
    country = serializers.CharField(max_length=10)


class SelectBusinessTypesSerializer(serializers.Serializer):
    business_types = serializers.ListField(
        child=serializers.CharField(max_length=64),
        allow_empty=False,
    )


class CreateStoreSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.CharField(max_length=60)


class OtpRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, required=False, allow_blank=True)
    channel = serializers.ChoiceField(choices=["email", "sms"], default="email", required=False)
    purpose = serializers.ChoiceField(choices=["login", "email_verify", "password_reset"], default="login", required=False)


class OtpVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, required=False, allow_blank=True)
    channel = serializers.ChoiceField(choices=["email", "sms"], default="email", required=False)
    purpose = serializers.ChoiceField(choices=["login", "email_verify", "password_reset"], default="login", required=False)
    code = serializers.CharField(max_length=12)


class OtpLoginRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)


class OtpLoginVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    code = serializers.CharField(max_length=12)
