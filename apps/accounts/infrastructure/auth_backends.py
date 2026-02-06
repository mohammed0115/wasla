from __future__ import annotations

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class PhoneOrEmailBackend(ModelBackend):
    """
    Authenticate with either:
    - username (we store merchant phone in username for now), or
    - email
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        identifier = str(username).strip()
        if not identifier:
            return None

        query = Q(**{f"{UserModel.USERNAME_FIELD}__iexact": identifier}) | Q(email__iexact=identifier)
        user = UserModel._default_manager.filter(query).order_by("id").first()
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

