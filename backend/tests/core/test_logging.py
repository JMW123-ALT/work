import structlog

from app.core.logging import get_logger


def test_structlog_baseline_is_configured():
    logger = get_logger("app.test").bind(component="unit-test")

    assert structlog.is_configured()
    assert hasattr(logger, "info")
    assert hasattr(logger, "bind")
