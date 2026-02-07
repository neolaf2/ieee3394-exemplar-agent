"""Smoke tests: ensure core modules import without requiring external services or API keys."""

def test_import_p3394_agent_package():
    import p3394_agent  # noqa: F401


def test_import_core_umf():
    from p3394_agent.core import umf  # noqa: F401
