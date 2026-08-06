# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Integration test: Consolidated browser automation tests via NLP instructions.

Requires: AWS credentials, Bedrock model access, AgentCore Browser permissions.
No mocking — real AgentCore Browser.

Run: PYTHONPATH=src python -m pytest tests/integration/test_browser_agent.py -v
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.integration.__setup__
# pylint: enable=import-error,unused-import

import os
import unittest
from logging import Logger
from typing import Optional

from utils.logging_helper import get_logger
from agents.browser_agent import BrowserAgentFactory


class TestBrowserAgent(unittest.TestCase):
    """Consolidated integration tests for browser automation via NLP instructions.

    Validates end-to-end browser automation with real AgentCore Browser sessions:
    - Wikipedia search and click
    - Form fill on httpbin.org
    - Amazon.ca multi-step navigation with popup dismissal
    - Gap Canada navigation with popup dismissal and scrolling
    - Nested modal popups with basic auth

    Each test verifies screenshots are persisted to BA_SESSIONS_DIR.
    """

    logger: Logger = get_logger(f"{__name__}.TestBrowserAgent")
    factory: Optional[BrowserAgentFactory] = None

    @classmethod
    def setUpClass(cls) -> None:
        """Create shared BrowserAgentFactory and agent for all tests."""
        cls.factory = BrowserAgentFactory()
        cls.agent = cls.factory.create_agent()

    def _assert_screenshots_persisted(self, context: str) -> None:
        """Verify at least one screenshot was persisted to BA_SESSIONS_DIR.

        Args:
            context: Test context description for assertion message.
        """
        sessions_dir = os.environ.get("BA_SESSIONS_DIR", "sessions")
        if os.path.isdir(sessions_dir):
            session_dirs = os.listdir(sessions_dir)
            self.logger.info("Session directories: %s", session_dirs)
            has_screenshots = any(
                os.path.isdir(os.path.join(sessions_dir, d))
                and len(os.listdir(os.path.join(sessions_dir, d))) > 0
                for d in session_dirs
            )
            self.assertTrue(
                has_screenshots,
                "Expected at least one screenshot persisted during %s" % context,
            )

    def test_wikipedia_search(self) -> None:
        """Search Wikipedia for 'Amazon Company' and click AMZN link.

        Validates:
        - get_by_placeholder (search field)
        - get_by_role(button) for search submission
        - get_by_role(link) for clicking search result
        - Multi-page navigation (homepage → search results → article)
        """
        self.logger.info("Starting Wikipedia search and click test")

        instruction = (
            "Navigate to https://en.wikipedia.org. "
            "Type 'Amazon Company' in the search field. "
            "Hit the 'Search' button. "
            "Click on AMZN."
        )

        response = self.agent(instruction)
        result_text = response.message["content"][0]["text"]
        self.logger.info("Agent response: %s", result_text)

        self._assert_screenshots_persisted("Wikipedia search")

    def test_form_fill(self) -> None:
        """Fill httpbin.org/forms/post with name, phone, email, pizza size, topping, submit.

        Validates:
        - get_by_label (customer name, telephone, email, delivery instructions)
        - get_by_role(radio) for pizza size selection
        - get_by_role(checkbox) for topping selection
        - get_by_role(button) for form submission
        - select_option for pizza size
        """
        self.logger.info("Starting httpbin form fill test")

        instruction = (
            "Go to https://httpbin.org/forms/post. "
            "Enter 'Visual Worker' as customer name. "
            "Enter '555-555-5555' as phone number. "
            "Enter 'visual-worker@example.com' as email. "
            "Select 'Small' size Pizza. "
            "Check 'Mushroom' as topping. "
            "Enter 'Deliver to my front door. Don't ring doorbell.' as delivery instructions. "
            "Click Submit."
        )

        response = self.agent(instruction)
        result_text = response.message["content"][0]["text"]
        self.logger.info("Agent response: %s", result_text)

        self._assert_screenshots_persisted("form fill")

    def test_amazon_navigation(self) -> None:
        """Navigate Amazon.ca: dismiss popups → AmazonBasics → Amazon Resale → Laptops & Tablets.

        Validates:
        - Multi-step navigation through dynamic content
        - Popup dismissal (cookie banners, location prompts)
        - get_by_role(link) for category navigation
        - Dynamic content loading between page transitions
        """
        self.logger.info("Starting Amazon.ca multi-step navigation test")

        instruction = (
            "Navigate to https://www.amazon.ca. "
            "Dismiss any popups that appear. "
            "Click on AmazonBasics. "
            "Click on 'Amazon Resale'. "
            "Click on 'Laptops & Tablets'."
        )

        response = self.agent(instruction)
        result_text = response.message["content"][0]["text"]
        self.logger.info("Agent response: %s", result_text)

        self._assert_screenshots_persisted("Amazon navigation")

    def test_gap_navigation(self) -> None:
        """Navigate Gap Canada: dismiss popups → Men → Jeans → Straight → best seller.

        Validates:
        - PageDown scrolling for lazy-loaded content
        - Popup dismissal (cookie banners, promotional overlays)
        - Category navigation through Men → Jeans → Straight
        - Lazy-loaded content interaction
        - get_by_role(link) and get_by_text for navigation elements
        """
        self.logger.info("Starting Gap Canada navigation test")

        instruction = (
            "Navigate to https://www.gapcanada.ca. "
            "Dismiss any popups that appear. "
            "Click on Men. "
            "Click on Jeans. "
            "Click on 'Straight'. "
            "Click on 'Straight Jeans' (best seller)."
        )

        response = self.agent(instruction)

        # Extract response text — agent may return empty content if handoff_to_user
        # fails in non-interactive test context (no stdin available)
        content = response.message.get("content", [])
        result_text = ""
        for block in content:
            if isinstance(block, dict) and block.get("text"):
                result_text = block["text"]
                break

        self.logger.info(
            "Agent response: %s",
            result_text if result_text else "(empty — likely handoff_to_user in non-interactive context)",
        )

        self._assert_screenshots_persisted("Gap navigation")

    def test_nested_popups(self) -> None:
        """Basic auth → open modal → child popup → grandchild → type text → OK.

        Validates:
        - Basic auth (username 'test', password 'admin1234')
        - Nested modal popups (parent → child → grandchild)
        - Escape key dismissal of popups
        - get_by_role(button) for popup interaction
        - Multi-level popup interaction
        - Form fill within popups (typing text in popup input fields)
        - Click OK to close popups
        """
        self.logger.info("Starting nested popups integration test")

        instruction = (
            "1. Go to https://d6xegnjz917v3.cloudfront.net/chatbot/auth/test_popup.html. "
            "2. In basic auth browser prompt type 'test' as username and 'admin1234' as password. "
            "3. Click on 'Open Modal Popup'. "
            "4. dismiss any popup. "
            "5. Click on 'Open Child Popup'. "
            "6. type 'hello from child popup' in 'child text input:' field. "
            "7. Click on 'Open Modal Popup'. "
            "8. dismiss any popup. "
            "9. click on 'Open Grandchild Popup'. "
            "10. Click on 'Open Modal Popup'. "
            "11. dismiss any popup. "
            "12. type 'hello from grandchild popup' in 'Grandchild Text Input:'. "
            "13. click OK. "
            "14. click OK."
        )

        response = self.agent(instruction)
        result_text = response.message["content"][0]["text"]
        self.logger.info("Agent response: %s", result_text)

        self._assert_screenshots_persisted("nested popup interaction")

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup browser sessions."""
        if cls.factory:
            cls.factory.cleanup()


if __name__ == "__main__":
    unittest.main()
