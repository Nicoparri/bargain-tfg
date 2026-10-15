"""Tests de integración del endpoint de salud (/api/v1/health/)."""

from unittest import mock

import pytest
from django.db import OperationalError

HEALTH_URLS = ["/api/v1/health/", "/api/health/"]


@pytest.mark.django_db
class TestHealthCheck:
    @pytest.mark.parametrize("url", HEALTH_URLS)
    def test_returns_ok_when_database_is_reachable(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "services": {"database": "ok"}}

    def test_returns_503_when_database_is_unreachable(self, api_client):
        with mock.patch(
            "apps.core.views.connection.ensure_connection",
            side_effect=OperationalError("database unavailable"),
        ):
            response = api_client.get(HEALTH_URLS[0])

        assert response.status_code == 503
        assert response.json() == {"status": "degraded", "services": {"database": "error"}}

    def test_is_public(self, api_client):
        api_client.credentials()  # sin cabecera Authorization
        response = api_client.get(HEALTH_URLS[0])

        assert response.status_code == 200
