from src.kairo_system import KairoSystem


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
    system = KairoSystem()

    health = system.execute_tool("browser", "health")

    assert health.status == "COMPLETED"
    assert health.result["status"] == "OPTIONAL_PROVIDER_UNAVAILABLE"
    assert system.health()["components"]["tools"]["providers"]["browser"]["status"] == (
        "OPTIONAL_PROVIDER_UNAVAILABLE"
    )


def test_browser_tool_does_not_fake_external_automation() -> None:
    system = KairoSystem()

    result = system.execute_tool(
        "browser",
        "navigate",
        {"url": "https://example.test"},
    )

    assert result.status == "FAILED"
    assert "No browser provider" in (result.error or "")
