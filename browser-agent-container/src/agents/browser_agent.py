# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Browser Agent factory — creates Strands Agent with visual browser tools."""

import os
from typing import Optional
from logging import Logger

from strands import Agent
from utils.logging_helper import get_logger
from tools.visual_browser_tool import VisualBrowserTool
from prompts.browser_system_prompt import BROWSER_AGENT_SYSTEM_PROMPT


class BrowserAgentFactory:
    """Creates and configures the browser automation Strands Agent.

    Reads configuration from environment variables:
    - AWS_DEFAULT_REGION: AWS region (default: us-west-2)
    - BA_BROWSER_MODEL_ID: Bedrock model ID (default: us.anthropic.claude-sonnet-4-5-20250929-v1:0)
    - BA_SESSION_TIMEOUT: Browser session timeout in seconds (default: 3600)

    Tool set:
    - browser (inherited from AgentCoreBrowser): navigation, keyboard, JS eval, session lifecycle
    - screenshot_for_vision: captures screenshot, returns ImageBlock, persists to disk
    - semantic_action: Playwright Locator API for element interaction
    - accessibility_snapshot: returns AXTree as structured text
    - handoff_to_user: WebSocket-backed HITL (NOT the Strands built-in — that one
      reads stdin and blocks in a headless container)
    """

    logger: Logger = get_logger(f"{__name__}.BrowserAgentFactory")

    def __init__(self) -> None:
        self.region: str = os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')
        self.model_id: str = os.environ.get(
            'BA_BROWSER_MODEL_ID',
            'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
        )
        self.session_timeout: int = int(os.environ.get('BA_SESSION_TIMEOUT', '3600'))
        self.browser_tool: Optional[VisualBrowserTool] = None

    def create_agent(self) -> Agent:
        """Create a Strands Agent with visual browser tools.

        Returns:
            Configured Strands Agent with browser, screenshot, semantic action,
            accessibility snapshot, and WebSocket-backed handoff_to_user tools.
        """
        self.browser_tool = VisualBrowserTool(
            region=self.region,
            session_timeout=self.session_timeout,
        )

        agent = Agent(
            tools=[
                self.browser_tool.browser,
                self.browser_tool.screenshot_for_vision,
                self.browser_tool.semantic_action,
                self.browser_tool.accessibility_snapshot,
                self.browser_tool.handoff_to_user,
            ],
            model=self.model_id,
            system_prompt=BROWSER_AGENT_SYSTEM_PROMPT,
        )

        self.logger.info(
            "Browser agent created: model=%s, region=%s, timeout=%ds",
            self.model_id, self.region, self.session_timeout,
        )
        return agent

    def cleanup(self) -> None:
        """Cleanup browser sessions."""
        if self.browser_tool:
            try:
                self.browser_tool._cleanup()
            except Exception as e:
                self.logger.warning("Cleanup error: %s", str(e))
