"""Tests unitarios de los permisos por rol de apps.core.permissions."""

from types import SimpleNamespace

import pytest

from apps.core.permissions import (
    IsBusiness,
    IsBusinessOwnerOrAdmin,
    IsConsumer,
    IsConsumerOrBusiness,
    IsOwnerOrAdmin,
)


def make_user(
    *,
    user_id: int = 0,
    authenticated: bool = True,
    consumer: bool = False,
    business: bool = False,
    staff: bool = False,
) -> SimpleNamespace:
    """Usuario mínimo con los atributos que consultan los permisos."""
    return SimpleNamespace(
        id=user_id,
        is_authenticated=authenticated,
        is_consumer=consumer,
        is_business=business,
        is_staff=staff,
    )


def make_request(user) -> SimpleNamespace:
    return SimpleNamespace(user=user)


# Cada usuario lleva un id distinto: SimpleNamespace compara por atributos, así que
# dos usuarios con el mismo rol e id serían "iguales" para la comprobación de propietario.
ANONYMOUS = make_user(user_id=1, authenticated=False)
CONSUMER = make_user(user_id=2, consumer=True)
BUSINESS = make_user(user_id=3, business=True)
STAFF = make_user(user_id=4, staff=True)


class TestRolePermissions:
    @pytest.mark.parametrize(
        ("user", "expected"),
        [(None, False), (ANONYMOUS, False), (CONSUMER, True), (BUSINESS, False)],
    )
    def test_is_consumer(self, user, expected):
        assert IsConsumer().has_permission(make_request(user), None) is expected

    @pytest.mark.parametrize(
        ("user", "expected"),
        [(None, False), (ANONYMOUS, False), (CONSUMER, False), (BUSINESS, True)],
    )
    def test_is_business(self, user, expected):
        assert IsBusiness().has_permission(make_request(user), None) is expected

    @pytest.mark.parametrize(
        ("user", "expected"),
        [
            (None, False),
            (ANONYMOUS, False),
            (CONSUMER, True),
            (BUSINESS, True),
            (make_user(user_id=5), False),
        ],
    )
    def test_is_consumer_or_business(self, user, expected):
        assert IsConsumerOrBusiness().has_permission(make_request(user), None) is expected


class TestIsOwnerOrAdmin:
    def test_anonymous_is_denied(self):
        obj = SimpleNamespace(user=ANONYMOUS)
        assert IsOwnerOrAdmin().has_object_permission(make_request(ANONYMOUS), None, obj) is False

    def test_missing_user_is_denied(self):
        obj = SimpleNamespace(user=CONSUMER)
        assert IsOwnerOrAdmin().has_object_permission(make_request(None), None, obj) is False

    def test_staff_is_allowed_on_any_object(self):
        obj = SimpleNamespace(user=CONSUMER)
        assert IsOwnerOrAdmin().has_object_permission(make_request(STAFF), None, obj) is True

    def test_owner_via_user_field_is_allowed(self):
        owner = make_user(user_id=10, consumer=True)
        obj = SimpleNamespace(user=owner)
        assert IsOwnerOrAdmin().has_object_permission(make_request(owner), None, obj) is True

    def test_owner_via_owner_field_is_allowed(self):
        owner = make_user(user_id=11, consumer=True)
        obj = SimpleNamespace(owner=owner)
        assert IsOwnerOrAdmin().has_object_permission(make_request(owner), None, obj) is True

    def test_other_user_is_denied(self):
        obj = SimpleNamespace(user=make_user(user_id=12, consumer=True))
        assert IsOwnerOrAdmin().has_object_permission(make_request(CONSUMER), None, obj) is False


class TestIsBusinessOwnerOrAdmin:
    def test_anonymous_is_denied(self):
        obj = SimpleNamespace(business=SimpleNamespace(user=BUSINESS))
        permission = IsBusinessOwnerOrAdmin()
        assert permission.has_object_permission(make_request(ANONYMOUS), None, obj) is False

    def test_staff_is_allowed(self):
        obj = SimpleNamespace(business=SimpleNamespace(user=BUSINESS))
        permission = IsBusinessOwnerOrAdmin()
        assert permission.has_object_permission(make_request(STAFF), None, obj) is True

    def test_non_business_user_is_denied(self):
        obj = SimpleNamespace(business=SimpleNamespace(user=CONSUMER))
        permission = IsBusinessOwnerOrAdmin()
        assert permission.has_object_permission(make_request(CONSUMER), None, obj) is False

    def test_owning_business_is_allowed(self):
        owner = make_user(user_id=13, business=True)
        obj = SimpleNamespace(business=SimpleNamespace(user=owner))
        permission = IsBusinessOwnerOrAdmin()
        assert permission.has_object_permission(make_request(owner), None, obj) is True

    def test_other_business_is_denied(self):
        obj = SimpleNamespace(business=SimpleNamespace(user=make_user(user_id=14, business=True)))
        permission = IsBusinessOwnerOrAdmin()
        assert permission.has_object_permission(make_request(BUSINESS), None, obj) is False

    def test_object_without_business_is_denied(self):
        obj = SimpleNamespace(business=None)
        permission = IsBusinessOwnerOrAdmin()
        assert not permission.has_object_permission(make_request(BUSINESS), None, obj)
