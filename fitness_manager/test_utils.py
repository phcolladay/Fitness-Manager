from copy import copy

from django.test.runner import DiscoverRunner


def patch_django_context_copy() -> None:
    """
    Keep Django 4.2's template test instrumentation working on Python 3.14.

    Django 4.2 copies template contexts with ``copy(super())``. Python 3.14 no
    longer lets that copied ``super`` object receive normal instance attrs, so
    the Django test client can fail while recording ``response.context``. The
    patch mirrors Django's intent by making a shallow instance copy directly.
    """
    from django.template.context import BaseContext

    if getattr(BaseContext.__copy__, "_fitness_manager_patch", False):
        return

    def _copy_base_context(self):
        duplicate = self.__class__.__new__(self.__class__)
        duplicate.__dict__ = self.__dict__.copy()
        duplicate.dicts = self.dicts[:]
        return duplicate

    _copy_base_context._fitness_manager_patch = True
    BaseContext.__copy__ = _copy_base_context


class PatchedDiscoverRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        patch_django_context_copy()
        return super().setup_test_environment(**kwargs)
