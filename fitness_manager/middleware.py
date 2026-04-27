from .showcase_data import ensure_guest_showcase_data, is_guest_user


class GuestShowcaseDataMiddleware:
    """
    Backfill showcase data for guest sessions created before guest seeding existed.
    """

    session_key = "guest_showcase_data_ready"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and is_guest_user(user) and not request.session.get(self.session_key):
            ensure_guest_showcase_data(user)
            request.session[self.session_key] = True
        return self.get_response(request)
