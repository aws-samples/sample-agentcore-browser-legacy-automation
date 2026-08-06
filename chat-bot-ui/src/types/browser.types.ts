// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Browser Agent profile — TypeScript type definitions.
 *
 * Single source of truth for browser-profile WebSocket frame shapes and UI-state
 * shapes. Values of `BrowserMessageType` mirror the backend constants defined in
 * `browser-agent-container/src/models/websocket_message_types.py` exactly
 * (case-sensitive) and MUST stay in lockstep with it.
 *
 * Convention note:
 * - snake_case keys (`session_id`, `conversation_history`) are used for shared
 *   chat/session payload fields.
 * - camelCase keys (`liveViewUrl`, `actionType`, `stepNumber`, `promptId`,
 *   `screenshotUrl`, `screenshotPath`, `currentUrl`, `screenshotBase64`) are
 *   used for browser-specific payload fields.
 *
 * This mixed convention is intentional and matches the backend wire format —
 * do NOT normalize to a single case style.
 */

// ---------------------------------------------------------------------------
// Shared chat/session types used by the browser profile.
// ---------------------------------------------------------------------------

/** Aggregated orchestration metadata attached to an assistant message. */
export interface OrchestrationData {
  steps: OrchestrationStep[];
  totalDurationMs: number;
  agentsInvoked: string[];
  agentsFailed: string[];
}

/** A single agent invocation step within an orchestration. */
export interface OrchestrationStep {
  agentId: string;
  agentName: string;
  status: 'running' | 'completed' | 'failed';
  durationMs?: number;
}

/** A source document returned by a specialist's vector store retrieval. */
export interface SourceDocument {
  type: string;
  excerpt?: string;
  excerpt_page_number?: number;
  score?: number;
  tool_call_id?: string;
  document_name?: string;
  document_url?: string;
}

/** A citation reference that maps to anchors in the response text. */
export interface Citation {
  ref: string;
  text: string;
  url?: string;
  document_name?: string;
  page?: number;
}

/** Per-agent metadata collected from A2A DataPart responses. */
export interface AgentMetadataEntry {
  sources?: SourceDocument[];
  citations?: Citation[];
  reasoning?: string;
  [key: string]: unknown;
}

/** A single chat message (user or assistant) displayed in the ChatView. */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  orchestration?: OrchestrationData;
  sources?: SourceDocument[];
  /** Per-agent metadata from A2A DataPart responses (sources, citations, etc.). */
  agentMetadata?: Record<string, AgentMetadataEntry>;
  /** True when this message represents an ERROR frame from the server. */
  isError?: boolean;
  /** Whether the error is recoverable (user can continue messaging). */
  recoverable?: boolean;
}

/** Represents a single session tracked in React state. */
export interface SessionInfo {
  session_id: string;
  profile: string;
  mode: 'text' | 'voice';
  title: string;
  created_at: string;
  messages: ChatMessage[];
}

// ---------------------------------------------------------------------------
// Frame type constants (9 client + 19 server = 28 total)
// ---------------------------------------------------------------------------

/**
 * All WebSocket message type strings used by the browser protocol.
 *
 * Client → Server (9): CONNECTION_INIT, CHAT_MESSAGE, BROWSER_STOP,
 *   BROWSER_HITL_RESPONSE, BROWSER_LIVE_VIEW_REQUEST, NEW_SESSION,
 *   RESUME_SESSION, GET_SESSIONS, DELETE_SESSION
 *
 * Server → Client — shared session/orchestration frames (11): CONNECTION_ESTABLISHED,
 *   SESSION_CREATED, SESSION_RESUMED, SESSIONS_LOADED, SESSION_DELETED,
 *   ORCHESTRATION_START, ORCHESTRATION_END, REASONING, STREAM, METADATA, ERROR
 *
 * Server → Client — browser-specific (8): BROWSER_SESSION_STARTED,
 *   BROWSER_ACTION_START, BROWSER_SCREENSHOT, BROWSER_ACTION_COMPLETE,
 *   BROWSER_HITL_PROMPT, BROWSER_HITL_TIMEOUT, BROWSER_LIVE_VIEW_URL,
 *   BROWSER_SESSION_ENDED
 */
export const BrowserMessageType = {
  // ─── Client → Server (9) ───
  CONNECTION_INIT: 'CONNECTION_INIT',
  CHAT_MESSAGE: 'CHAT_MESSAGE',
  BROWSER_STOP: 'BROWSER_STOP',
  BROWSER_HITL_RESPONSE: 'BROWSER_HITL_RESPONSE',
  BROWSER_LIVE_VIEW_REQUEST: 'BROWSER_LIVE_VIEW_REQUEST',
  NEW_SESSION: 'NEW_SESSION',
  RESUME_SESSION: 'RESUME_SESSION',
  GET_SESSIONS: 'GET_SESSIONS',
  DELETE_SESSION: 'DELETE_SESSION',

  // ─── Server → Client — Shared session/orchestration frames (11) ───
  CONNECTION_ESTABLISHED: 'CONNECTION_ESTABLISHED',
  SESSION_CREATED: 'SESSION_CREATED',
  SESSION_RESUMED: 'SESSION_RESUMED',
  SESSIONS_LOADED: 'SESSIONS_LOADED',
  SESSION_DELETED: 'SESSION_DELETED',
  ORCHESTRATION_START: 'ORCHESTRATION_START',
  ORCHESTRATION_END: 'ORCHESTRATION_END',
  REASONING: 'REASONING',
  STREAM: 'STREAM',
  METADATA: 'METADATA',
  ERROR: 'ERROR',

  // ─── Server → Client — Browser-specific (7) ───
  BROWSER_SESSION_STARTED: 'BROWSER_SESSION_STARTED',
  BROWSER_ACTION_START: 'BROWSER_ACTION_START',
  BROWSER_SCREENSHOT: 'BROWSER_SCREENSHOT',
  BROWSER_ACTION_COMPLETE: 'BROWSER_ACTION_COMPLETE',
  BROWSER_HITL_PROMPT: 'BROWSER_HITL_PROMPT',
  BROWSER_HITL_TIMEOUT: 'BROWSER_HITL_TIMEOUT',
  BROWSER_LIVE_VIEW_URL: 'BROWSER_LIVE_VIEW_URL',
  BROWSER_SESSION_ENDED: 'BROWSER_SESSION_ENDED',
} as const;

/** Union type of all browser message type string values. */
export type BrowserMessageTypeValue =
  (typeof BrowserMessageType)[keyof typeof BrowserMessageType];

// ---------------------------------------------------------------------------
// Browser-specific chat message extensions
// ---------------------------------------------------------------------------

/** Screenshot entry attached to an assistant message (one per BROWSER_SCREENSHOT frame). */
export interface BrowserScreenshotEntry {
  stepNumber: number;
  /** Pre-signed S3 URL (~4h lifetime; UI does not re-sign). */
  screenshotUrl: string;
  /** S3 object key (for logs / debugging). */
  screenshotPath: string;
  title: string;
  /** Epoch milliseconds. */
  timestamp: number;
}

/** Action progress entry attached to an assistant message. Matched to its
 *  BROWSER_ACTION_COMPLETE partner by `stepNumber`, not by arrival order. */
export interface BrowserActionEntry {
  stepNumber: number;
  /** 'browser' | 'semantic_action' | 'screenshot_for_vision' |
   *  'accessibility_snapshot' | 'handoff_to_user' (open-ended). */
  actionType: string;
  details: string;
  status: 'running' | 'succeeded' | 'failed';
  result?: string;
}

/** Human-In-The-Loop prompt attached to an assistant message. */
export interface BrowserHitlPromptEntry {
  promptId: string;
  question: string;
  options: string[];
  context: string;
  /** Optional base64-encoded inline image (HITL prompts are bounded and small). */
  screenshotBase64?: string;
  status: 'pending' | 'responded' | 'timeout';
}

/** Chat message carrying optional browser-specific rendering artifacts. */
export interface BrowserChatMessage extends ChatMessage {
  screenshots?: BrowserScreenshotEntry[];
  actions?: BrowserActionEntry[];
  hitlPrompt?: BrowserHitlPromptEntry;
}

// ---------------------------------------------------------------------------
// UI state
// ---------------------------------------------------------------------------

/** UI state for the currently active browser automation session. */
export interface BrowserSessionState {
  isActive: boolean;
  liveViewUrl: string | null;
  stepCounter: number;
  pendingHitl: BrowserHitlPromptEntry | null;
}

// ---------------------------------------------------------------------------
// WebSocket message interfaces — Client → Server (9)
// ---------------------------------------------------------------------------

/** Sent immediately after WebSocket `open` to trigger the backend handshake. */
export interface BrowserConnectionInitMessage {
  type: typeof BrowserMessageType.CONNECTION_INIT;
}

/** User NLP instruction sent to the browser agent. */
export interface BrowserChatMessageOut {
  type: typeof BrowserMessageType.CHAT_MESSAGE;
  content: string;
}

/** User requests mid-automation termination. */
export interface BrowserStopMessage {
  type: typeof BrowserMessageType.BROWSER_STOP;
}

/** Response to a prior BROWSER_HITL_PROMPT. */
export interface BrowserHitlResponseMessage {
  type: typeof BrowserMessageType.BROWSER_HITL_RESPONSE;
  promptId: string;
  action: string;
  value?: string;
}

/** Request a fresh pre-signed DCV URL (DCV URLs expire ≤ 300 s). */
export interface BrowserLiveViewRequestMessage {
  type: typeof BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST;
}

/** Create a new session on the existing connection. */
export interface BrowserNewSessionMessage {
  type: typeof BrowserMessageType.NEW_SESSION;
}

/** Resume a previous session by ID. */
export interface BrowserResumeSessionMessage {
  type: typeof BrowserMessageType.RESUME_SESSION;
  session_id: string;
}

/** Request the session list. */
export interface BrowserGetSessionsMessage {
  type: typeof BrowserMessageType.GET_SESSIONS;
}

/** Delete a session by ID. */
export interface BrowserDeleteSessionMessage {
  type: typeof BrowserMessageType.DELETE_SESSION;
  session_id: string;
}

/** Discriminated union of all client → server browser messages. */
export type BrowserClientMessage =
  | BrowserConnectionInitMessage
  | BrowserChatMessageOut
  | BrowserStopMessage
  | BrowserHitlResponseMessage
  | BrowserLiveViewRequestMessage
  | BrowserNewSessionMessage
  | BrowserResumeSessionMessage
  | BrowserGetSessionsMessage
  | BrowserDeleteSessionMessage;

// ---------------------------------------------------------------------------
// WebSocket message interfaces — Server → Client (19)
// ---------------------------------------------------------------------------

/** Handshake response. The browser variant has NO `available_agents` field —
 *  this is the single-profile reference implementation's only handshake shape. */
export interface ConnectionEstablishedMessage {
  type: typeof BrowserMessageType.CONNECTION_ESTABLISHED;
  session_id: string;
  profile: string;
}

/** Confirms a new session was created. */
export interface SessionCreatedMessage {
  type: typeof BrowserMessageType.SESSION_CREATED;
  session_id: string;
}

/** Returns a resumed session with conversation history. */
export interface SessionResumedMessage {
  type: typeof BrowserMessageType.SESSION_RESUMED;
  session_id: string;
  conversation_history: Array<{
    role: string;
    content: string;
    timestamp?: number;
  }>;
}

/** Session summary item returned in SESSIONS_LOADED for the browser profile.
 *
 * The backend's ``BrowserHandler._handle_get_sessions`` emits a flat dict
 * per session — the hook maps each entry into a full ``SessionInfo`` when
 * processing ``SESSIONS_LOADED``. ``profile`` and ``mode`` are optional on
 * the wire (defensive against older container builds) but the mapping
 * defaults them to ``"browser"`` and ``"text"`` respectively so the shared
 * ``SessionList`` component renders the correct icon and routes resume
 * clicks to the browser profile. See Issue 1 in
 * ``.kiro/research/temp-browser-ui-issues-analysis.md``.
 */
export interface BrowserSessionSummary {
  session_id: string;
  profile?: string;
  mode?: 'text' | 'voice';
  created_at: string;
  message_count: number;
  first_message_preview: string;
  status?: string;
}

/** Returns the list of previous sessions. */
export interface SessionsLoadedMessage {
  type: typeof BrowserMessageType.SESSIONS_LOADED;
  sessions: BrowserSessionSummary[];
}

/** Confirms a session was deleted from the store. */
export interface SessionDeletedMessage {
  type: typeof BrowserMessageType.SESSION_DELETED;
  session_id: string;
}

/** Marks the start of orchestration processing. */
export interface OrchestrationStartMessage {
  type: typeof BrowserMessageType.ORCHESTRATION_START;
}

/** Marks the end of orchestration processing. */
export interface OrchestrationEndMessage {
  type: typeof BrowserMessageType.ORCHESTRATION_END;
}

/** LLM reasoning text. */
export interface ReasoningMessage {
  type: typeof BrowserMessageType.REASONING;
  content: string;
}

/** A streaming token of the synthesized answer. */
export interface StreamMessage {
  type: typeof BrowserMessageType.STREAM;
  content: string;
}

/** Orchestration metadata. The browser variant has NO `agents_invoked` or
 *  `agent_metadata` fields — browser is a single-agent profile. */
export interface MetadataMessage {
  type: typeof BrowserMessageType.METADATA;
  total_duration_ms: number;
  steps_completed: number;
}

/** Error frame with recovery information. */
export interface ErrorMessage {
  type: typeof BrowserMessageType.ERROR;
  content: string;
  recoverable: boolean;
}

/** Emitted once per session-start — announces the DCV live-view URL. */
export interface BrowserSessionStartedMessage {
  type: typeof BrowserMessageType.BROWSER_SESSION_STARTED;
  session_id: string;
  liveViewUrl: string;
}

/** Announces the start of a browser action (navigate, click, etc.). */
export interface BrowserActionStartMessage {
  type: typeof BrowserMessageType.BROWSER_ACTION_START;
  actionType: string;
  details: string;
  stepNumber: number;
}

/** Delivers a screenshot via pre-signed S3 URL. */
export interface BrowserScreenshotMessage {
  type: typeof BrowserMessageType.BROWSER_SCREENSHOT;
  screenshotPath: string;
  screenshotUrl: string;
  timestamp: number;
  title: string;
  stepNumber: number;
}

/** Reports the result of a previously-started action. Paired with
 *  BROWSER_ACTION_START by matching `stepNumber`. */
export interface BrowserActionCompleteMessage {
  type: typeof BrowserMessageType.BROWSER_ACTION_COMPLETE;
  actionType: string;
  result: string;
  success: boolean;
  stepNumber: number;
  currentUrl: string;
}

/** Human-In-The-Loop prompt — rendered inline as an assistant chat message. */
export interface BrowserHitlPromptMessage {
  type: typeof BrowserMessageType.BROWSER_HITL_PROMPT;
  promptId: string;
  question: string;
  options: string[];
  context: string;
  screenshotBase64: string;
}

/** Signals that a pending HITL prompt went 300 s without a response. */
export interface BrowserHitlTimeoutMessage {
  type: typeof BrowserMessageType.BROWSER_HITL_TIMEOUT;
  session_id: string;
}

/** Response to a client-initiated BROWSER_LIVE_VIEW_REQUEST. */
export interface BrowserLiveViewUrlMessage {
  type: typeof BrowserMessageType.BROWSER_LIVE_VIEW_URL;
  session_id: string;
  liveViewUrl: string;
}

/** Browser automation session terminated (user stop or natural completion). */
export interface BrowserSessionEndedMessage {
  type: typeof BrowserMessageType.BROWSER_SESSION_ENDED;
  session_id: string;
  reason: 'stopped' | 'completed';
}

/** Discriminated union of all server → client browser messages. */
export type BrowserServerMessage =
  | ConnectionEstablishedMessage
  | SessionCreatedMessage
  | SessionResumedMessage
  | SessionsLoadedMessage
  | SessionDeletedMessage
  | OrchestrationStartMessage
  | OrchestrationEndMessage
  | ReasoningMessage
  | StreamMessage
  | MetadataMessage
  | ErrorMessage
  | BrowserSessionStartedMessage
  | BrowserActionStartMessage
  | BrowserScreenshotMessage
  | BrowserActionCompleteMessage
  | BrowserHitlPromptMessage
  | BrowserHitlTimeoutMessage
  | BrowserLiveViewUrlMessage
  | BrowserSessionEndedMessage;
