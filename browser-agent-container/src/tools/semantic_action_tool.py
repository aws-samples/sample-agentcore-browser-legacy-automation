# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""SemanticActionTool — maps SemanticActionInput to Playwright Locator API calls."""

from typing import Any, Dict
from logging import Logger

from utils.logging_helper import get_logger
from tools.models import SemanticActionInput


class SemanticActionTool:
    """Executes browser actions using Playwright's semantic Locator API."""

    logger: Logger = get_logger(f"{__name__}.SemanticActionTool")

    def __init__(self, browser_tool: Any) -> None:
        """Initialize with a reference to the parent VisualBrowserTool.

        Args:
            browser_tool: VisualBrowserTool instance (provides get_session_page,
                          validate_session, _execute_async).
        """
        self.browser_tool = browser_tool

    def execute(self, si: SemanticActionInput) -> Dict[str, Any]:
        """Execute a semantic browser action.

        Args:
            si: SemanticActionInput with locator type, parameters, and action.

        Returns:
            Tool result with success/error status and description.
        """
        self.logger.debug("Executing semantic action: session=%s, locator=%s, action=%s",
                          si.session_name, si.locator_type, si.action)

        error = self.browser_tool.validate_session(si.session_name)
        if error:
            self.logger.error("Session validation failed: session=%s", si.session_name)
            return error

        page = self.browser_tool.get_session_page(si.session_name)
        if not page:
            self.logger.error("No active page for session: %s", si.session_name)
            return {"status": "error", "content": [{"text": "No active page"}]}

        try:
            # Enter iframe if specified
            target = page
            if si.frame_selector:
                self.logger.debug("Entering iframe: %s", si.frame_selector)
                target = page.frame_locator(si.frame_selector)

            # Build locator
            locator = self._build_locator(target, si)

            # Apply filters
            if si.filter_text:
                locator = locator.filter(has_text=si.filter_text)
            if si.filter_not_text:
                locator = locator.filter(has_not_text=si.filter_not_text)
            if si.nth is not None:
                locator = locator.nth(si.nth)

            # Execute action
            return self._execute_action(locator, si)

        except Exception as e:
            self.logger.error("Semantic action failed: %s", str(e))
            return {"status": "error", "content": [{"text": f"Error: {str(e)}"}]}

    def _build_locator(self, target: Any, si: SemanticActionInput) -> Any:
        """Build a Playwright Locator from the input parameters.

        Args:
            target: Page or FrameLocator to build the locator on.
            si: SemanticActionInput with locator type and parameters.

        Returns:
            Playwright Locator instance.

        Raises:
            ValueError: If the required parameter for the chosen locator_type is missing.
        """
        self.logger.debug("Building locator: type=%s", si.locator_type)

        # Validate that the required parameter for the chosen locator_type is provided
        locator_param_map: Dict[str, str] = {
            "role": "role", "label": "label", "text": "text",
            "placeholder": "placeholder", "alt_text": "alt_text",
            "title": "title_text", "test_id": "test_id",
        }
        required_param = locator_param_map.get(si.locator_type)
        if required_param and getattr(si, required_param) is None:
            raise ValueError(
                f"locator_type='{si.locator_type}' requires '{required_param}' parameter"
            )

        if si.locator_type == "role":
            kwargs: Dict[str, Any] = {}
            if si.name is not None:
                kwargs["name"] = si.name
            # Design choice: exact intentionally omitted for get_by_role —
            # default case-insensitive substring matching is more forgiving
            # for AI-driven automation.
            if si.checked is not None:
                kwargs["checked"] = si.checked
            if si.disabled is not None:
                kwargs["disabled"] = si.disabled
            if si.expanded is not None:
                kwargs["expanded"] = si.expanded
            if si.pressed is not None:
                kwargs["pressed"] = si.pressed
            if si.selected is not None:
                kwargs["selected"] = si.selected
            if si.level is not None:
                kwargs["level"] = si.level
            if si.include_hidden is not None:
                kwargs["include_hidden"] = si.include_hidden
            return target.get_by_role(si.role, **kwargs)
        elif si.locator_type == "label":
            return target.get_by_label(si.label, exact=si.exact)
        elif si.locator_type == "text":
            return target.get_by_text(si.text, exact=si.exact)
        elif si.locator_type == "placeholder":
            return target.get_by_placeholder(si.placeholder, exact=si.exact)
        elif si.locator_type == "alt_text":
            return target.get_by_alt_text(si.alt_text, exact=si.exact)
        elif si.locator_type == "title":
            return target.get_by_title(si.title_text, exact=si.exact)
        elif si.locator_type == "test_id":
            return target.get_by_test_id(si.test_id)
        else:
            raise ValueError(f"Unknown locator_type: {si.locator_type}")

    def _execute_action(self, locator: Any, si: SemanticActionInput) -> Dict[str, Any]:
        """Execute the specified action on the locator.

        Args:
            locator: Playwright Locator to act on.
            si: SemanticActionInput with action and parameters.

        Returns:
            Tool result with success/error status and description.
        """
        # Validate required parameters for the chosen action
        action_required_params: Dict[str, str] = {
            "fill": "value", "press": "key", "press_sequentially": "value",
            "set_input_files": "files", "get_attribute": "attribute_name",
        }
        required = action_required_params.get(si.action)
        if required and getattr(si, required) is None:
            return {
                "status": "error",
                "content": [{"text": f"Action '{si.action}' requires '{required}' parameter"}],
            }

        # Build description using the locator parameter that matches locator_type
        locator_desc_map: Dict[str, Any] = {
            "role": si.name, "label": si.label, "text": si.text,
            "placeholder": si.placeholder, "alt_text": si.alt_text,
            "title": si.title_text, "test_id": si.test_id,
        }
        desc = f"{si.action} on {si.locator_type}="
        desc += locator_desc_map.get(si.locator_type) or "?"

        if si.action == "click":
            kwargs: Dict[str, Any] = {}
            if si.button:
                kwargs["button"] = si.button
            if si.click_count:
                kwargs["click_count"] = si.click_count
            if si.modifiers:
                kwargs["modifiers"] = si.modifiers
            if si.timeout:
                kwargs["timeout"] = si.timeout
            if si.force:
                kwargs["force"] = si.force
            self.browser_tool._execute_async(locator.click(**kwargs))
        elif si.action == "dblclick":
            kwargs = {}
            if si.button:
                kwargs["button"] = si.button
            if si.modifiers:
                kwargs["modifiers"] = si.modifiers
            if si.timeout:
                kwargs["timeout"] = si.timeout
            if si.force:
                kwargs["force"] = si.force
            self.browser_tool._execute_async(locator.dblclick(**kwargs))
        elif si.action == "fill":
            kwargs = {}
            if si.timeout:
                kwargs["timeout"] = si.timeout
            if si.force:
                kwargs["force"] = si.force
            self.browser_tool._execute_async(locator.fill(si.value or "", **kwargs))
            desc += f" value='{si.value}'"
        elif si.action == "clear":
            self.browser_tool._execute_async(locator.clear())
        elif si.action == "check":
            kwargs = {}
            if si.timeout:
                kwargs["timeout"] = si.timeout
            if si.force:
                kwargs["force"] = si.force
            self.browser_tool._execute_async(locator.check(**kwargs))
        elif si.action == "uncheck":
            kwargs = {}
            if si.timeout:
                kwargs["timeout"] = si.timeout
            if si.force:
                kwargs["force"] = si.force
            self.browser_tool._execute_async(locator.uncheck(**kwargs))
        elif si.action == "select_option":
            kwargs = {}
            if si.timeout:
                kwargs["timeout"] = si.timeout
            # Note: select_option() does NOT accept force — unlike click/fill/check.
            if si.option_label:
                self.browser_tool._execute_async(
                    locator.select_option(label=si.option_label, **kwargs)
                )
                desc += f" label='{si.option_label}'"
            elif si.option_index is not None:
                self.browser_tool._execute_async(
                    locator.select_option(index=si.option_index, **kwargs)
                )
                desc += f" index={si.option_index}"
            else:
                self.browser_tool._execute_async(
                    locator.select_option(si.value, **kwargs)
                )
                desc += f" value='{si.value}'"
        elif si.action == "hover":
            kwargs = {}
            if si.timeout:
                kwargs["timeout"] = si.timeout
            if si.force:
                kwargs["force"] = si.force
            self.browser_tool._execute_async(locator.hover(**kwargs))
        elif si.action == "focus":
            self.browser_tool._execute_async(locator.focus())
        elif si.action == "blur":
            self.browser_tool._execute_async(locator.blur())
        elif si.action == "press":
            self.browser_tool._execute_async(locator.press(si.key))
            desc += f" key='{si.key}'"
        elif si.action == "press_sequentially":
            kwargs = {}
            if si.delay:
                kwargs["delay"] = si.delay
            self.browser_tool._execute_async(
                locator.press_sequentially(si.value, **kwargs)
            )
            desc += f" text='{si.value}'"
        elif si.action == "set_input_files":
            self.browser_tool._execute_async(locator.set_input_files(si.files))
        elif si.action == "scroll_into_view":
            self.browser_tool._execute_async(locator.scroll_into_view_if_needed())
        elif si.action == "get_text":
            text = self.browser_tool._execute_async(locator.inner_text())
            return {"status": "success", "content": [{"text": f"Element text: {text}"}]}
        elif si.action == "get_attribute":
            val = self.browser_tool._execute_async(
                locator.get_attribute(si.attribute_name)
            )
            return {"status": "success", "content": [{"text": f"Attribute '{si.attribute_name}': {val}"}]}
        elif si.action == "get_value":
            val = self.browser_tool._execute_async(locator.input_value())
            return {"status": "success", "content": [{"text": f"Input value: {val}"}]}
        elif si.action == "count":
            count = self.browser_tool._execute_async(locator.count())
            return {"status": "success", "content": [{"text": f"Found {count} matching elements"}]}
        elif si.action == "is_visible":
            visible = self.browser_tool._execute_async(locator.is_visible())
            return {"status": "success", "content": [{"text": f"Element visible: {visible}"}]}
        else:
            return {"status": "error", "content": [{"text": f"Unknown action: {si.action}"}]}

        self.logger.info("Semantic action: %s", desc)
        return {"status": "success", "content": [{"text": desc}]}
