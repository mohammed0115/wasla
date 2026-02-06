from __future__ import annotations

from django import forms


class MerchantSignupForm(forms.Form):
    full_name = forms.CharField(max_length=200, label="الاسم الكامل")
    phone = forms.CharField(max_length=32, label="رقم الجوال")
    email = forms.EmailField(max_length=254, label="البريد الإلكتروني")
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        min_length=8,
    )
    accept_terms = forms.BooleanField(label="أوافق على الشروط والأحكام", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ["full_name", "phone", "email", "password"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.setdefault("class", "form-control")
        if "accept_terms" in self.fields:
            self.fields["accept_terms"].widget.attrs.setdefault("class", "form-check-input")


class MerchantLoginForm(forms.Form):
    identifier = forms.CharField(max_length=254, label="الجوال أو البريد الإلكتروني")
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ["identifier", "password"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.setdefault("class", "form-control")
