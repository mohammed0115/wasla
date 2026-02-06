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


class SelectCountrySerializer(serializers.Serializer):
    country = serializers.CharField(max_length=10)


class SelectBusinessTypesSerializer(serializers.Serializer):
    business_types = serializers.ListField(
        child=serializers.CharField(max_length=64),
        allow_empty=False,
    )
