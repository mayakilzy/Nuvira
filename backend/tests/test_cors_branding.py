"""Production brand and CORS configuration regression coverage."""

from app.config import settings


PRODUCTION_ORIGIN = "https://nuvira.agentcraft.info"


def test_nuvira_is_the_default_application_identity():
    assert settings.APP_NAME == "Nuvira"
    assert settings.FRONTEND_URL == PRODUCTION_ORIGIN


def test_production_frontend_origin_is_allowed_by_cors(client):
    response = client.options(
        "/health",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PRODUCTION_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
