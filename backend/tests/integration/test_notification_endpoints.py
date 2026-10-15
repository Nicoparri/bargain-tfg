"""Tests de integración de los endpoints REST de notificaciones y tokens push."""

import pytest

from apps.notifications.models import Notification, NotificationType, UserPushToken

BASE_URL = "/api/v1/notifications/"
PUSH_TOKEN_URL = "/api/v1/notifications/push-token/"


def make_notification(user, *, is_read: bool = False, title: str = "Bajada de precio"):
    return Notification.objects.create(
        user=user,
        notification_type=NotificationType.PRICE_ALERT,
        title=title,
        body="El producto vigilado ha bajado de precio.",
        is_read=is_read,
    )


@pytest.mark.django_db
class TestNotificationEndpoints:
    def test_requires_authentication(self, api_client):
        assert api_client.get(BASE_URL).status_code == 401

    def test_mark_single_notification_as_read(self, authenticated_client, consumer_user):
        notification = make_notification(consumer_user)

        response = authenticated_client.patch(f"{BASE_URL}{notification.id}/read/")

        assert response.status_code == 200
        assert response.json()["success"] is True
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_read_all_marks_only_own_unread_notifications(
        self, authenticated_client, consumer_user, business_user
    ):
        make_notification(consumer_user)
        make_notification(consumer_user)
        make_notification(consumer_user, is_read=True)
        other = make_notification(business_user)

        response = authenticated_client.post(f"{BASE_URL}read-all/")

        assert response.status_code == 200
        assert response.json()["data"] == {"marked_read": 2}
        assert not Notification.objects.filter(user=consumer_user, is_read=False).exists()
        other.refresh_from_db()
        assert other.is_read is False

    def test_unread_count_ignores_read_and_deleted(self, authenticated_client, consumer_user):
        make_notification(consumer_user)
        make_notification(consumer_user, is_read=True)
        deleted = make_notification(consumer_user)
        authenticated_client.delete(f"{BASE_URL}{deleted.id}/")

        response = authenticated_client.get(f"{BASE_URL}unread-count/")

        assert response.status_code == 200
        assert response.json()["data"] == {"count": 1}

    def test_delete_is_soft(self, authenticated_client, consumer_user):
        notification = make_notification(consumer_user)

        response = authenticated_client.delete(f"{BASE_URL}{notification.id}/")

        assert response.status_code == 204
        notification.refresh_from_db()
        assert notification.deleted_at is not None
        assert authenticated_client.get(f"{BASE_URL}{notification.id}/").status_code == 404

    def test_cannot_read_other_users_notification(self, authenticated_client, business_user):
        notification = make_notification(business_user)

        response = authenticated_client.patch(f"{BASE_URL}{notification.id}/read/")

        assert response.status_code == 404
        notification.refresh_from_db()
        assert notification.is_read is False


@pytest.mark.django_db
class TestPushTokenEndpoint:
    def test_creates_token_for_new_device(self, authenticated_client, consumer_user):
        payload = {"token": "ExponentPushToken[abc]", "device_id": "iphone-1"}

        response = authenticated_client.post(PUSH_TOKEN_URL, payload)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["token"] == "ExponentPushToken[abc]"
        assert data["device_id"] == "iphone-1"
        assert UserPushToken.objects.filter(user=consumer_user).count() == 1

    def test_updates_token_for_existing_device(self, authenticated_client, consumer_user):
        UserPushToken.objects.create(
            user=consumer_user, device_id="iphone-1", token="ExponentPushToken[old]"
        )

        response = authenticated_client.post(
            PUSH_TOKEN_URL, {"token": "ExponentPushToken[new]", "device_id": "iphone-1"}
        )

        assert response.status_code == 200
        assert response.json()["data"]["token"] == "ExponentPushToken[new]"
        assert UserPushToken.objects.filter(user=consumer_user).count() == 1

    def test_rejects_blank_token(self, authenticated_client):
        response = authenticated_client.post(PUSH_TOKEN_URL, {"token": "   "})

        assert response.status_code == 400
