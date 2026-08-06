# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Pydantic models for the semantic_action tool."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class SemanticActionInput(BaseModel):
    """Interact with a web page element using Playwright semantic locators.

    Step 1: Choose a locator_type and provide its required parameter.
    Step 2: Choose an action and provide its required parameters.
    Step 3: Optionally narrow results with filter_text, nth, or frame_selector.
    """

    session_name: str = Field(
        pattern=r"^[a-z0-9-]+$",
        description=(
            "Browser session name from a previous init_session call. "
            "Must be the SAME name used across all tool calls in this session."
        ),
    )

    # ── Step 1: Locator ──────────────────────────────────────────────
    locator_type: Literal[
        "role", "label", "text", "placeholder",
        "alt_text", "title", "test_id",
    ] = Field(description="How to locate the element on the page.")

    # Locator parameters
    role: Optional[str] = Field(
        default=None,
        description=(
            "ARIA role (for locator_type='role'). Common values: "
            "button, link, checkbox, radio, textbox, combobox, "
            "listitem, heading, tab, option, menuitem, dialog, "
            "alert, img, navigation, search."
        ),
    )
    name: Optional[str] = Field(
        default=None,
        description="Accessible name of the element (for locator_type='role').",
    )
    label: Optional[str] = Field(
        default=None,
        description="Label text (for locator_type='label').",
    )
    text: Optional[str] = Field(
        default=None,
        description="Visible text content (for locator_type='text').",
    )
    placeholder: Optional[str] = Field(
        default=None,
        description="Placeholder hint text (for locator_type='placeholder').",
    )
    alt_text: Optional[str] = Field(
        default=None,
        description="Image alt text (for locator_type='alt_text').",
    )
    title_text: Optional[str] = Field(
        default=None,
        description=(
            "Title/tooltip text (for locator_type='title'). "
            "Renamed from 'title' to avoid Pydantic v2 JSON schema collision."
        ),
    )
    test_id: Optional[str] = Field(
        default=None,
        description="data-testid attribute value (for locator_type='test_id').",
    )
    exact: bool = Field(
        default=False,
        description=(
            "If True, match text exactly (case-sensitive, whole-string). "
            "If False (default), match as case-insensitive substring."
        ),
    )

    # Role-specific filters (only used with locator_type='role')
    checked: Optional[bool] = Field(
        default=None,
        description="Filter checkboxes/radios by checked state. Only for locator_type='role'.",
    )
    disabled: Optional[bool] = Field(
        default=None,
        description="Filter by disabled state. Only for locator_type='role'.",
    )
    expanded: Optional[bool] = Field(
        default=None,
        description="Filter by expanded state (accordions, dropdowns). Only for locator_type='role'.",
    )
    pressed: Optional[bool] = Field(
        default=None,
        description="Filter toggle buttons by pressed state. Only for locator_type='role'.",
    )
    selected: Optional[bool] = Field(
        default=None,
        description="Filter options/tabs by selected state. Only for locator_type='role'.",
    )
    level: Optional[int] = Field(
        default=None,
        description="Heading level 1-6 (for role='heading'). Only for locator_type='role'.",
    )
    include_hidden: Optional[bool] = Field(
        default=None,
        description="Include hidden elements. Only for locator_type='role'.",
    )

    # ── Narrowing (optional) ─────────────────────────────────────────
    filter_text: Optional[str] = Field(
        default=None,
        description="Narrow results to elements containing this text.",
    )
    filter_not_text: Optional[str] = Field(
        default=None,
        description="Exclude elements containing this text.",
    )
    nth: Optional[int] = Field(
        default=None,
        description="Select the nth match (0-based). Use 0 for first, -1 for last.",
    )
    frame_selector: Optional[str] = Field(
        default=None,
        description="CSS selector for an iframe to enter before locating the element.",
    )

    # ── Step 2: Action ───────────────────────────────────────────────
    action: Literal[
        "click", "dblclick", "fill", "clear", "check", "uncheck",
        "select_option", "hover", "focus", "blur", "press",
        "press_sequentially", "set_input_files", "scroll_into_view",
        "get_text", "get_attribute", "get_value", "count", "is_visible",
    ] = Field(description="Action to perform on the located element.")

    # Action parameters
    value: Optional[str] = Field(
        default=None,
        description="Text value for 'fill', 'press_sequentially', or 'select_option' (by value).",
    )
    option_label: Optional[str] = Field(
        default=None,
        description="Visible label text for 'select_option' action.",
    )
    option_index: Optional[int] = Field(
        default=None,
        description="Zero-based index for 'select_option' action.",
    )
    attribute_name: Optional[str] = Field(
        default=None,
        description="Attribute name for 'get_attribute' action (e.g., 'href', 'src', 'class').",
    )
    files: Optional[List[str]] = Field(
        default=None,
        description="File path(s) for 'set_input_files' action.",
    )
    key: Optional[str] = Field(
        default=None,
        description="Key for 'press' action (e.g., 'Enter', 'Tab', 'Escape', 'ArrowDown').",
    )
    button: Optional[str] = Field(
        default=None,
        description="Mouse button for 'click'/'dblclick': 'left' (default), 'right', 'middle'.",
    )
    click_count: Optional[int] = Field(
        default=None,
        description="Number of clicks for 'click' action. Use 2 for double-click, 3 for triple-click.",
    )
    delay: Optional[int] = Field(
        default=None,
        description="Delay in milliseconds between characters for 'press_sequentially'.",
    )
    modifiers: Optional[List[Literal["Shift", "Control", "Alt", "Meta"]]] = Field(
        default=None,
        description=(
            "Keyboard modifiers held during 'click'/'dblclick': "
            "['Shift'], ['Control'], ['Alt'], ['Meta']."
        ),
    )
    timeout: Optional[int] = Field(
        default=None,
        description="Action timeout in milliseconds. Override the default 30s timeout.",
    )
    force: Optional[bool] = Field(
        default=None,
        description="If True, bypass Playwright actionability checks.",
    )
