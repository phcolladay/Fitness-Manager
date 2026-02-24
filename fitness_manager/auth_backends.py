from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        login_value = username or kwargs.get(UserModel.USERNAME_FIELD)
        if not login_value or not password:
            return None
        user = None
        try:
            if "@" in login_value:
                user = UserModel.objects.filter(email__iexact=login_value).first()
            else:
                user = UserModel.objects.filter(username__iexact=login_value).first()
        except Exception:  # noqa: BLE001
            return None
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

