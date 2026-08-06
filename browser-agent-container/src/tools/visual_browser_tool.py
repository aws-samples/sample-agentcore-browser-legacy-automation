# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""VisualBrowserTool — subclasses AgentCoreBrowser, delegates to ScreenshotTool, SemanticActionTool, and AccessibilityTool."""

from typing import Any, Dict, Optional, Tuple
from logging import Logger

from playwright.async_api import Page, Browser as PlaywrightBrowser
from strands_tools.browser import AgentCoreBrowser
from bedrock_agentcore.tools.browser_client import BrowserClient as AgentCoreBrowserClient
from strands import tool
from utils.logging_helper import get_logger

from handlers.screenshot_storage import ScreenshotStorageBase
from tools.screenshot_tool import ScreenshotTool
from tools.semantic_action_tool import SemanticActionTool
from tools.accessibility_tool import AccessibilityTool
from tools.handoff_to_user_tool import HandoffToUserTool
from tools.models import SemanticActionInput


# Generate flat inputSchema from SemanticActionInput at module load time.
# This eliminates the nested {"semantic_input": {...}} wrapper that the default
# @tool decorator produces when the parameter is a Pydantic model. Claude struggles
# with the nested wrapper — it tries to pass fields flat, gets validation errors,
# and falls back to the simpler browser(click) tool. A flat schema lets Claude
# produce {"session_name": "...", "locator_type": "role", "action": "click", ...}
# directly, which works reliably across Sonnet/Opus/Haiku models.
_SEMANTIC_ACTION_SCHEMA: Dict[str, Any] = {
    "json": SemanticActionInput.model_json_schema()
}


class VisualBrowserTool(AgentCoreBrowser):
    """AgentCoreBrowser extended with screenshot vision, semantic locator, and accessibility tree capabilities.

    Registers four tools on a single instance:
    - browser (inherited) — navigation, keyboard, JS eval, session lifecycle
    - screenshot_for_vision — captures screenshot, returns ImageBlock, persists to disk
    - semantic_action — Playwright Locator API for element interaction
    - accessibility_snapshot — returns AXTree as structured text for fast element identification

    The hybrid AXTree + Vision approach (inspired by Browser-Use and Playwright MCP Server)
    provides two independent signals for element identification:
    - AXTree: fast (~100ms), cheap (~200-2000 tokens), works well on semantic HTML
    - Screenshot: slower (~3-5s), costlier (~1334 tokens/image), works on any page including legacy
    """

    logger: Logger = get_logger(f"{__name__}.VisualBrowserTool")

    def __init__(self, storage: Optional[ScreenshotStorageBase] = None, **kwargs: Any) -> None:
        """Initialize VisualBrowserTool with delegate tool instances.

        Args:
            storage: Optional ScreenshotStorageBase for screenshot persistence.
            **kwargs: Passed through to AgentCoreBrowser (region, session_timeout, etc.).
        """
        super().__init__(**kwargs)
        self._screenshot_tool = ScreenshotTool(self, storage=storage)
        self._semantic_tool = SemanticActionTool(self)
        self._accessibility_tool = AccessibilityTool(self)
        self._handoff_tool = HandoffToUserTool()
        self.logger.debug(
            "VisualBrowserTool initialized with screenshot, semantic, "
            "accessibility, and handoff tools"
        )

    def _execute_async(self, action_coro: Any) -> Any:
        """Run an async coroutine on the browser's private event loop.

        Overrides Browser._execute_async to skip nest_asyncio.apply().

        The upstream implementation calls nest_asyncio.apply() which patches
        asyncio.BaseEventLoop at the CLASS level — corrupting Uvicorn's main
        event loop and causing WebSocket connections to drop after ~15s on
        AgentCore Runtime.

        This override is safe because Strands dispatches tool calls via
        asyncio.to_thread(), which runs this method in a separate thread
        with no running event loop. The browser's private loop
        (self._loop, created in Browser.__init__) can use run_until_complete
        without nesting.

        See: .kiro/research/browser-agent-agentcore-event-loop-research.md
        """
        return self._loop.run_until_complete(action_coro)

    async def create_browser_session(self) -> PlaywrightBrowser:
        """Create a browser session and store the BrowserClient for live view URL generation.

        Overrides AgentCoreBrowser.create_browser_session() to store the
        BrowserClient in _client_dict before returning. The upstream implementation
        creates the client as a local variable that goes out of scope, losing
        access to generate_live_view_url(), take_control(), release_control(),
        and preventing close_platform() from stopping sessions.
        """
        if not self._playwright:
            raise RuntimeError("Playwright not initialized")

        session_client = AgentCoreBrowserClient(region=self.region)
        session_id = session_client.start(
            identifier=self.identifier,
            session_timeout_seconds=self.session_timeout,
        )

        self.logger.info(
            "Browser session started: agentcore_session_id=%s identifier=%s",
            session_id, self.identifier,
        )

        cdp_url, cdp_headers = session_client.generate_ws_headers()
        browser = await self._playwright.chromium.connect_over_cdp(
            endpoint_url=cdp_url, headers=cdp_headers,
        )

        # Store client for live view URL generation and proper cleanup.
        # The upstream AgentCoreBrowser never populates _client_dict.
        self._client_dict[session_id] = session_client

        # Generate and log live view URL for debugging
        try:
            live_view_url = session_client.generate_live_view_url()
            self.logger.debug(
                "Live view URL: session=%s url=%s",
                session_id, live_view_url,
            )
        except Exception as e:
            self.logger.warning("Failed to generate live view URL: %s", str(e))

        return browser

    def get_live_view_url(self, expires: int = 300) -> str:
        """Generate a fresh pre-signed live view URL for the active browser session.

        Args:
            expires: Seconds until URL expires (max 300, default 300).

        Returns:
            Pre-signed URL string, or empty string if no active client.
        """
        for client in self._client_dict.values():
            if client.session_id:
                try:
                    url = client.generate_live_view_url(expires=expires)
                    self.logger.debug(
                        "Live view URL generated: session=%s expires=%ds",
                        client.session_id, expires,
                    )
                    return url
                except Exception as e:
                    self.logger.warning(
                        "Failed to generate live view URL: %s", str(e),
                    )
        return ""

    async def _setup_session_from_browser(self, browser_or_context: Any) -> Tuple[Any, Any, Any]:
        """Setup session with automatic window.open() popup detection.

        Overrides AgentCoreBrowser._setup_session_from_browser to register a
        context-level ``page`` event listener. When a page calls ``window.open()``
        or a link has ``target="_blank"``, Playwright creates a new Page in the
        same BrowserContext. This listener auto-registers that page as a tab in
        the BrowserSession so that get_active_page() returns the popup and all
        tools (semantic_action, accessibility_snapshot, screenshot_for_vision)
        automatically operate on it.

        When the popup closes itself (``window.close()``), the tab is removed
        and the active tab falls back to the parent page.
        """
        browser, context, page = await super()._setup_session_from_browser(browser_or_context)

        def _on_new_page(new_page: Page) -> None:
            """Handle window.open() popups by registering them as session tabs."""
            for session_name, session in self._sessions.items():
                if session.context is context:
                    tab_id = "popup_%d" % len(session.tabs)
                    session.add_tab(tab_id, new_page)
                    self.logger.info(
                        "Popup auto-registered: session=%s tab=%s url=%s",
                        session_name, tab_id, new_page.url,
                    )

                    # Auto-remove tab when popup closes itself (window.close())
                    def _on_popup_close(_page: Any = None, sess=session, tid: str = tab_id, sname: str = session_name) -> None:
                        sess.remove_tab(tid)
                        self.logger.info(
                            "Popup auto-removed: session=%s tab=%s",
                            sname, tid,
                        )

                    new_page.on("close", _on_popup_close)
                    break

        context.on("page", _on_new_page)
        return browser, context, page

    @tool
    def screenshot_for_vision(self, session_name: str, title: str, full_page: bool = False) -> Dict[str, Any]:
        """Capture a screenshot and return it as an image for visual analysis.

        Persists the screenshot via pluggable storage at
        {user_id}/{session_id}/screenshots/{timestamp}_{title}.png.

        Call this AFTER navigating to a page and AFTER every semantic_action.
        For well-structured pages, prefer accessibility_snapshot first (faster, cheaper).
        Use this when the accessibility tree is sparse or you need visual confirmation.

        Args:
            session_name: Browser session name from init_session.
            title: Descriptive title (e.g., 'homepage-after-navigation', 'before-clicking-submit').
            full_page: If True, capture entire page. Default: viewport only.
        """
        return self._screenshot_tool.capture(session_name, title, full_page)

    @tool(inputSchema=_SEMANTIC_ACTION_SCHEMA)
    def semantic_action(self, **kwargs: Any) -> Dict[str, Any]:
        """Interact with a page element using Playwright semantic locators.

        Finds elements by visible label, role, text, or placeholder — no CSS selectors needed.

        Use accessibility_snapshot or screenshot_for_vision first to identify elements,
        then call this with the visible text/label you identified.

        Args:
            **kwargs: Flat parameters matching SemanticActionInput fields
                (session_name, locator_type, action, role, name, label, text, etc.).
        """
        # Accept both flat kwargs (from Claude via flat schema) and the legacy
        # nested wrapper (from existing callers that pass semantic_input=...).
        if "semantic_input" in kwargs:
            si = kwargs["semantic_input"]
            if isinstance(si, dict):
                si = SemanticActionInput(**si)
        else:
            si = SemanticActionInput(**kwargs)
        return self._semantic_tool.execute(si)

    @tool
    def accessibility_snapshot(self, session_name: str) -> Dict[str, Any]:
        """Return the page's accessibility tree as structured text.

        This is the FAST, CHEAP way to understand page structure (~100ms, ~200-2000 tokens).
        Use this FIRST before screenshot_for_vision. If the tree shows rich semantic
        structure (roles, labels, names), use it to identify elements for semantic_action.
        If the tree is sparse (legacy apps with no ARIA roles), fall back to screenshot_for_vision.

        Args:
            session_name: Browser session name from init_session.
        """
        return self._accessibility_tool.snapshot(session_name)

    @tool
    def handoff_to_user(
        self, message: str, breakout_of_loop: bool = False,
    ) -> Dict[str, Any]:
        """Hand off control to the human user and wait for their response.

        Use this tool when you need clarification, confirmation, or a human
        decision that you cannot determine yourself. Emits a `BROWSER_HITL_PROMPT`
        frame to the connected WebSocket client and blocks the agent loop until
        the client sends back a `BROWSER_HITL_RESPONSE`. The browser microVM
        session stays alive the entire time.

        Args:
            message: The question or instruction to present to the user.
                Include enough context that the user can respond without
                re-reading the full conversation.
            breakout_of_loop: Accepted for compatibility with
                `strands_tools.handoff_to_user`; ignored. This tool always
                waits for the user's response because the WebSocket chat flow
                depends on Claude resuming with the answer.
        """
        # Delegate to the composed HandoffToUserTool instance so the
        # WebSocket wiring lives in one place.
        return self._handoff_tool.invoke(
            message=message, breakout_of_loop=breakout_of_loop,
        )

# ---------------------------------------------------------------------------
# Patch semantic_action's Strands validation model to accept flat parameters.
#
# The @tool decorator auto-generates a Pydantic wrapper model from the function
# signature. With **kwargs, it creates a model with a single "kwargs" field,
# which rejects flat input from Claude. We replace it with a model whose fields
# match SemanticActionInput directly, so Strands validates flat params correctly
# before passing them as **kwargs to the method.
# ---------------------------------------------------------------------------
from pydantic import create_model as _create_model  # noqa: E402

_FlatSemanticInputModel = _create_model(
    "FlatSemanticInput",
    **{
        name: (field.annotation, field.default)
        for name, field in SemanticActionInput.model_fields.items()
    },
)

# The tool is a descriptor on the class — access it via __dict__ to get the
# DecoratedFunctionTool without triggering __get__.
_semantic_tool_descriptor = VisualBrowserTool.__dict__["semantic_action"]
if hasattr(_semantic_tool_descriptor, "_metadata"):
    _semantic_tool_descriptor._metadata.input_model = _FlatSemanticInputModel
