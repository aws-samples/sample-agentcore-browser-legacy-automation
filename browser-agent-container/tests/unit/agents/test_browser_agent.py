# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Unit tests for BrowserAgentFactory.
"""

import tests.__setup__  # noqa: F401
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from agents.browser_agent import BrowserAgentFactory
from prompts.browser_system_prompt import BROWSER_AGENT_SYSTEM_PROMPT


class TestBrowserAgentFactoryDefaults(unittest.TestCase):
    """Test BrowserAgentFactory reads env vars with defaults when vars absent."""

    @patch.dict("os.environ", {}, clear=True)
    def test_default_region(self) -> None:
        """Default region is us-west-2 when AWS_DEFAULT_REGION absent."""
        factory = BrowserAgentFactory()
        self.assertEqual(factory.region, "us-west-2")

    @patch.dict("os.environ", {}, clear=True)
    def test_default_model_id(self) -> None:
        """Default model ID when BA_BROWSER_MODEL_ID absent."""
        factory = BrowserAgentFactory()
        self.assertEqual(
            factory.model_id,
            "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_default_session_timeout(self) -> None:
        """Default session timeout is 3600 when BA_SESSION_TIMEOUT absent."""
        factory = BrowserAgentFactory()
        self.assertEqual(factory.session_timeout, 3600)

    @patch.dict("os.environ", {
        "AWS_DEFAULT_REGION": "eu-west-1",
        "BA_BROWSER_MODEL_ID": "custom-model-id",
        "BA_SESSION_TIMEOUT": "7200",
    })
    def test_reads_custom_env_vars(self) -> None:
        """Factory reads custom values from environment variables."""
        factory = BrowserAgentFactory()
        self.assertEqual(factory.region, "eu-west-1")
        self.assertEqual(factory.model_id, "custom-model-id")
        self.assertEqual(factory.session_timeout, 7200)

    @patch.dict("os.environ", {}, clear=True)
    def test_browser_tool_initially_none(self) -> None:
        """browser_tool is None before create_agent() is called."""
        factory = BrowserAgentFactory()
        self.assertIsNone(factory.browser_tool)


class TestBrowserAgentFactoryCreateAgent(unittest.TestCase):
    """Test create_agent creates VisualBrowserTool and Agent correctly."""

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_creates_visual_browser_tool_with_defaults(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent creates VisualBrowserTool with default region and timeout."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        mock_vbt_cls.assert_called_once_with(
            region="us-west-2",
            session_timeout=3600,
        )

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {
        "AWS_DEFAULT_REGION": "ap-southeast-1",
        "BA_SESSION_TIMEOUT": "1800",
    })
    def test_creates_visual_browser_tool_with_custom_values(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent passes custom region and timeout to VisualBrowserTool."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        mock_vbt_cls.assert_called_once_with(
            region="ap-southeast-1",
            session_timeout=1800,
        )

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_creates_agent_with_five_tools(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent creates Agent with 5 tools."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        call_kwargs = mock_agent_cls.call_args
        tools = call_kwargs.kwargs.get("tools") or call_kwargs[1].get("tools")
        self.assertEqual(len(tools), 5)

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_creates_agent_with_correct_tools(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent includes browser, screenshot, semantic, accessibility, and handoff tools."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        call_kwargs = mock_agent_cls.call_args
        tools = call_kwargs.kwargs.get("tools") or call_kwargs[1].get("tools")

        # Verify the browser tool methods are included
        self.assertIn(mock_vbt_instance.browser, tools)
        self.assertIn(mock_vbt_instance.screenshot_for_vision, tools)
        self.assertIn(mock_vbt_instance.semantic_action, tools)
        self.assertIn(mock_vbt_instance.accessibility_snapshot, tools)

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_registers_visual_browser_tool_handoff_not_strands_builtin(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """The 5th tool is `VisualBrowserTool.handoff_to_user`, not
        `strands_tools.handoff_to_user`.

        Regression guard: the Strands built-in handoff_to_user reads stdin via
        prompt_toolkit, which blocks forever in a headless container. The
        agent MUST register our custom WebSocket-backed implementation
        instead. This test asserts the registered 5th tool is the bound
        method on the browser_tool instance.
        """
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        call_kwargs = mock_agent_cls.call_args
        tools = call_kwargs.kwargs.get("tools") or call_kwargs[1].get("tools")

        # Must be the method on the visual browser tool, not an import from
        # strands_tools.
        self.assertIn(mock_vbt_instance.handoff_to_user, tools)

    @patch.dict("os.environ", {}, clear=True)
    def test_does_not_import_strands_tools_handoff_to_user(self) -> None:
        """Regression guard: the agent module must not import the stdin-blocking
        strands_tools.handoff_to_user symbol. Keeping that import around would
        make it too easy to accidentally re-register it.
        """
        import agents.browser_agent as module

        # The module should not have a bound attribute named handoff_to_user
        # imported from strands_tools.
        imported_handoff = getattr(module, "handoff_to_user", None)
        self.assertIsNone(
            imported_handoff,
            msg=(
                "agents.browser_agent.handoff_to_user is still present — "
                "the Strands built-in has been re-imported. Remove the import."
            ),
        )

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_creates_agent_with_system_prompt(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent passes BROWSER_AGENT_SYSTEM_PROMPT to Agent."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        call_kwargs = mock_agent_cls.call_args
        system_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt")
        self.assertEqual(system_prompt, BROWSER_AGENT_SYSTEM_PROMPT)

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_creates_agent_with_model_id(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent passes model_id to Agent."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        call_kwargs = mock_agent_cls.call_args
        model = call_kwargs.kwargs.get("model") or call_kwargs[1].get("model")
        self.assertEqual(model, "us.anthropic.claude-sonnet-4-5-20250929-v1:0")

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_stores_browser_tool_reference(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent stores the VisualBrowserTool instance on the factory."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()

        self.assertIs(factory.browser_tool, mock_vbt_instance)

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_returns_agent_instance(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """create_agent returns the Agent instance."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance
        mock_agent_instance = MagicMock()
        mock_agent_cls.return_value = mock_agent_instance

        factory = BrowserAgentFactory()
        result = factory.create_agent()

        self.assertIs(result, mock_agent_instance)


class TestBrowserAgentFactoryCleanup(unittest.TestCase):
    """Test cleanup() calls _cleanup() on browser tool."""

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_cleanup_calls_browser_tool_cleanup(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """cleanup() calls _cleanup() on the browser tool."""
        mock_vbt_instance = MagicMock()
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()
        factory.cleanup()

        mock_vbt_instance._cleanup.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    def test_cleanup_without_create_agent_does_nothing(self) -> None:
        """cleanup() does nothing if create_agent() was never called."""
        factory = BrowserAgentFactory()
        # Should not raise
        factory.cleanup()

    @patch("agents.browser_agent.Agent")
    @patch("agents.browser_agent.VisualBrowserTool")
    @patch.dict("os.environ", {}, clear=True)
    def test_cleanup_handles_exception_gracefully(
        self, mock_vbt_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """cleanup() catches exceptions from _cleanup() without re-raising."""
        mock_vbt_instance = MagicMock()
        mock_vbt_instance._cleanup.side_effect = RuntimeError("cleanup failed")
        mock_vbt_cls.return_value = mock_vbt_instance

        factory = BrowserAgentFactory()
        factory.create_agent()
        # Should not raise
        factory.cleanup()


if __name__ == "__main__":
    unittest.main()
