"""Redis/Celery gate. Run while the isolated staging worker is healthy."""

import os

import pytest

BROKER = os.getenv("FOUNDATION_CELERY_BROKER_URL")
BACKEND = os.getenv("FOUNDATION_CELERY_RESULT_BACKEND")
pytestmark = pytest.mark.skipif(
    not (BROKER and BACKEND),
    reason="FOUNDATION_CELERY_BROKER_URL and FOUNDATION_CELERY_RESULT_BACKEND are not configured",
)


def test_worker_registration_ping_and_result_persistence():
    from app.workers.celery_app import celery_app

    celery_app.conf.update(broker_url=BROKER, result_backend=BACKEND)
    registered = celery_app.control.inspect(timeout=10).registered()
    assert registered and any("app.workers.tasks.ping" in tasks for tasks in registered.values())
    assert any("process_curriculum_resource" in tasks for tasks in registered.values())
    result = celery_app.send_task("app.workers.tasks.ping")
    assert result.get(timeout=20) == "pong"
