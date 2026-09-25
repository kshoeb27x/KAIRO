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


def test_browser_tool_does_not_fake_external_automation() -> None:
    system = KairoSystem()

    result = system.execute_tool(
        "browser",
        "navigate",
        {"url": "https://example.test"},
    )

    assert result.status == "FAILED"
    assert "No browser provider" in (result.error or "")
