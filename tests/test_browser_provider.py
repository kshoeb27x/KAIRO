from src.kairo_system import KairoSystem

AuthorityLevel = __import__(
    "06_SECURITY.Authority.authority",
    fromlist=["AuthorityLevel"],
).AuthorityLevel


def authorized_system():
    system = KairoSystem()
    system.security.identity.create("browser-test", "Browser Test")
    system.security.authority.assign(
        "browser-test",
        AuthorityLevel.USER,
    )
    system.security.permissions.grant(
        "browser-test",
        "network.read",
    )
    context = system.security.context(
        "browser-test",
        "network.read",
        "tool.browser",
        "browser",
    )
    return system, context


class FakeBrowserProvider:
    def __init__(self) -> None:
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {"action": request.action, "arguments": request.arguments}

    def health(self):
        return {"status": "ONLINE", "provider": "fake"}


def test_browser_provider_contract_is_optional_and_executable() -> None:
    browser = __import__(
        "04_TOOLS.Browser.tool",
        fromlist=["BrowserTool"],
    ).BrowserTool(FakeBrowserProvider())

    result = browser.execute("navigate", {"url": "https://example.test"})

    assert result["action"] == "navigate"
    assert result["arguments"]["url"] == "https://example.test"


def test_browser_health_reports_optional_provider_state() -> None:
    system, context = authorized_system()

    health = system.execute_tool(
        "browser",
        "health",
        context=context,
    )

    assert health.status == "COMPLETED"
    assert health.result["status"] == "OPTIONAL_PROVIDER_UNAVAILABLE"
    assert system.health()["components"]["tools"]["providers"]["browser"]["status"] == (
        "OPTIONAL_PROVIDER_UNAVAILABLE"
    )


def test_browser_tool_does_not_fake_external_automation() -> None:
    system, context = authorized_system()

    result = system.execute_tool(
        "browser",
        "navigate",
        {"url": "https://example.test"},
        context=context,
    )

    assert result.status == "FAILED"
    assert "No browser provider" in (result.error or "")
