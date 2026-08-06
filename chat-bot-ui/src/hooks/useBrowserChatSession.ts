// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * useBrowserChatSession — WebSocket lifecycle hook for browser-agent chat.
 *
 * Manages the full connection lifecycle with the Browser Agent backend via the
 * NGINX gateway (`wss://<gateway>/ws?token=<oidc>&profile=browser`):
 * - CONNECTION_INIT → CONNECTION_ESTABLISHED handshake
 * - CHAT_MESSAGE / BROWSER_HITL_RESPONSE with HITL auto-swap
 * - Streaming frame sequence (orchestration → REASONING / STREAM / METADATA)
 * - Browser-specific frame sequence (BROWSER_SESSION_STARTED, BROWSER_ACTION_*,
 *   BROWSER_SCREENSHOT, BROWSER_HITL_*, BROWSER_LIVE_VIEW_URL,
 *   BROWSER_SESSION_ENDED)
 * - Exponential backoff reconnection (max 5 retries, max 30s delay)
 * - Session management (NEW_SESSION, RESUME_SESSION, GET_SESSIONS,
 *   DELETE_SESSION)
 * - Live-view URL refresh requests (BROWSER_LIVE_VIEW_REQUEST)
 * - Mid-automation stop (BROWSER_STOP)
 *
 * State machine:
 *   disconnected → connecting → connected → streaming → connected
 *   connected → disconnect() → disconnected
 *   connected → abnormal close → reconnecting (backoff) → error (after max retries)
 *
 * Mirrors the structure of `useTextChatSession.ts` so shared plumbing
 * (reconnection, session list, open/close) stays consistent across profiles.
 *
 * @module hooks/useBrowserChatSession
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import type { ChatMessage, SessionInfo } from '../types/browser.types';
import type {
  BrowserChatMessage,
  BrowserSessionState,
  BrowserActionEntry,
  BrowserScreenshotEntry,
  BrowserHitlPromptEntry,
  BrowserServerMessage,
} from '../types/browser.types';
import { BrowserMessageType } from '../types/browser.types';
import { buildWebSocketUrl } from '../utils/websocket';

// ---------------------------------------------------------------------------
// Constants (identical to useTextChatSession — Req 15.6)
// ---------------------------------------------------------------------------

const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30_000;
const MAX_RETRIES = 5;

/** Initial UI state for a browser automation session. */
const INITIAL_BROWSER_SESSION: BrowserSessionState = {
  isActive: false,
  liveViewUrl: null,
  stepCounter: 0,
  pendingHitl: null,
};

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/** Connection state machine values. */
export type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'streaming'
  | 'error';

/** Return type of the useBrowserChatSession hook. */
export interface UseBrowserChatSessionReturn {
  connectionState: ConnectionState;
  sessionId: string | null;
  messages: BrowserChatMessage[];
  sessions: SessionInfo[];
  isStreaming: boolean;
  browserSession: BrowserSessionState;

  // Outgoing dispatchers
  sendMessage: (content: string) => void;
  sendHitlResponse: (action: string, value?: string) => void;
  stopBrowser: () => void;
  requestLiveViewUrl: () => void;
  newSession: () => void;
  resumeSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  getSessions: () => void;

  // Lifecycle
  connect: (token: string, profile: string) => void;
  disconnect: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Generate a unique message ID. */
const generateMessageId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
};

/** Get an ISO timestamp string for the current moment. */
const now = (): string => new Date().toISOString();

/** Guarded dev-mode console.warn — silenced in production builds (Req 17.3/17.4). */
const devWarn = (...args: unknown[]): void => {
  if (typeof __DEV_MODE__ !== 'undefined' && __DEV_MODE__) {
    // eslint-disable-next-line no-console
    console.warn(...args);
  }
};

/** Find the index of the last assistant message in the array. */
function findLastAssistantIndex(msgs: BrowserChatMessage[]): number {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant') return i;
  }
  return -1;
}

/** Ensure the message list has a trailing assistant message to attach artifacts to. */
function ensureAssistantMessage(msgs: BrowserChatMessage[]): BrowserChatMessage[] {
  if (findLastAssistantIndex(msgs) !== -1) return msgs;
  const placeholder: BrowserChatMessage = {
    id: generateMessageId(),
    role: 'assistant',
    content: '',
    timestamp: now(),
    isStreaming: true,
  };
  return [...msgs, placeholder];
}

// ---------------------------------------------------------------------------
// Hook implementation
// ---------------------------------------------------------------------------

/**
 * Manages the WebSocket connection to the Browser Agent backend.
 *
 * @returns Connection state, messages, session helpers, browser session state,
 *   and outgoing-frame dispatchers.
 */
export const useBrowserChatSession = (): UseBrowserChatSessionReturn => {
  // ---- React state (triggers re-renders) ----
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<BrowserChatMessage[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [browserSession, setBrowserSession] =
    useState<BrowserSessionState>(INITIAL_BROWSER_SESSION);

  // ---- Refs (stable across renders, no stale closures) ----
  const wsRef = useRef<WebSocket | null>(null);
  const tokenRef = useRef<string>('');
  const profileRef = useRef<string>('');
  const retryCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isUserDisconnectRef = useRef(false);
  /** Latest pendingHitl — read synchronously by sendMessage/sendHitlResponse. */
  const pendingHitlRef = useRef<BrowserHitlPromptEntry | null>(null);
  /** Ref to hold the latest connectInternal for reconnection (avoids stale closure). */
  const connectInternalRef = useRef<(token: string, profile: string) => void>(() => {});

  // ---- State helpers (update ref + setState together where needed) ----

  const updateMessages = useCallback(
    (updater: (prev: BrowserChatMessage[]) => BrowserChatMessage[]) => {
      setMessages((prev) => updater(prev));
    },
    [],
  );

  const updateBrowserSession = useCallback(
    (updater: (prev: BrowserSessionState) => BrowserSessionState) => {
      setBrowserSession((prev) => {
        const next = updater(prev);
        pendingHitlRef.current = next.pendingHitl;
        return next;
      });
    },
    [],
  );

  // ---- WebSocket send helper ----

  const wsSend = useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }, []);

  // ---- Message-manipulation helpers ----

  /**
   * Update the last assistant message via a pure updater.
   * If no assistant message exists yet, a placeholder is appended first so the
   * artifact has somewhere to attach.
   */
  const updateCurrentAssistant = useCallback(
    (updater: (msg: BrowserChatMessage) => BrowserChatMessage) => {
      updateMessages((prev) => {
        const seeded = ensureAssistantMessage(prev);
        const idx = findLastAssistantIndex(seeded);
        if (idx === -1) return seeded;
        const next = [...seeded];
        next[idx] = updater(next[idx]);
        return next;
      });
    },
    [updateMessages],
  );

  // ---- Server-frame handler ----

  const handleServerMessage = useCallback(
    (data: BrowserServerMessage) => {
      switch (data.type) {
        // ─── Shared session/orchestration frames ───────────────────────

        case BrowserMessageType.CONNECTION_ESTABLISHED: {
          // Req 2.3 — store session_id, set 'connected', do NOT read available_agents.
          retryCountRef.current = 0;
          setSessionId(data.session_id);
          setConnectionState('connected');
          // Req 2.4 — auto-fetch session list.
          wsSend({ type: BrowserMessageType.GET_SESSIONS });
          break;
        }

        case BrowserMessageType.SESSION_CREATED: {
          // Req 4.2 — new session, clear messages.
          setSessionId(data.session_id);
          updateMessages(() => []);
          break;
        }

        case BrowserMessageType.SESSION_RESUMED: {
          // Req 4.3 — resume, replace messages with history.
          setSessionId(data.session_id);
          const restored: BrowserChatMessage[] = (data.conversation_history || []).map(
            (entry) => ({
              id: generateMessageId(),
              role: entry.role === 'user' ? 'user' : 'assistant',
              content: entry.content,
              timestamp: now(),
            }),
          );
          updateMessages(() => restored);
          // Reset browser-session view state on resume — new session context.
          updateBrowserSession(() => INITIAL_BROWSER_SESSION);
          break;
        }

        case BrowserMessageType.SESSIONS_LOADED: {
          // Req 4.4 — set sessions state from the payload array.
          //
          // The backend sends each session as a summary dict (session_id,
          // profile, mode, created_at, message_count, first_message_preview,
          // status). The shared `SessionList` component renders `SessionInfo`,
          // which needs `title` + an empty `messages` array. We map here with
          // defensive `profile: 'browser', mode: 'text'` fallbacks so that an
          // older container version missing those fields still renders the
          // correct icon and click-routing (Issue 1 in
          // .kiro/research/temp-browser-ui-issues-analysis.md).
          const mapped: SessionInfo[] = (data.sessions || []).map((s) => ({
            session_id: s.session_id,
            profile: s.profile ?? 'browser',
            mode: s.mode ?? 'text',
            title: s.first_message_preview || 'Untitled session',
            created_at: s.created_at,
            messages: [],
          }));
          setSessions(mapped);
          break;
        }

        case BrowserMessageType.SESSION_DELETED: {
          // Req 4.5 — remove matching session_id from sessions.
          setSessions((prev) => prev.filter((s) => s.session_id !== data.session_id));
          break;
        }

        case BrowserMessageType.ORCHESTRATION_START: {
          // Req 4.6.
          setIsStreaming(true);
          setConnectionState('streaming');
          // Seed an assistant message so later artifacts have a target.
          updateMessages((prev) => ensureAssistantMessage(prev));
          break;
        }

        case BrowserMessageType.ORCHESTRATION_END: {
          // Req 4.7.
          setIsStreaming(false);
          setConnectionState('connected');
          updateCurrentAssistant((msg) => ({ ...msg, isStreaming: false }));
          break;
        }

        case BrowserMessageType.REASONING: {
          // Req 4.8 — append to reasoning section (stashed under the
          // 'browser' key of agentMetadata as a single AgentMetadataEntry).
          updateCurrentAssistant((msg) => {
            const existing = msg.agentMetadata ?? {};
            const prior = existing.browser ?? {};
            const currentReasoning =
              typeof prior.reasoning === 'string' ? prior.reasoning : '';
            return {
              ...msg,
              agentMetadata: {
                ...existing,
                browser: {
                  ...prior,
                  reasoning: currentReasoning + data.content,
                },
              },
            };
          });
          break;
        }

        case BrowserMessageType.STREAM: {
          // Req 4.9 — append to main content.
          updateCurrentAssistant((msg) => ({
            ...msg,
            content: msg.content + data.content,
          }));
          break;
        }

        case BrowserMessageType.METADATA: {
          // Req 4.10 — attach total_duration_ms + steps_completed under the
          // 'browser' key; do NOT read agents_invoked / agent_metadata
          // (absent in the browser protocol).
          updateCurrentAssistant((msg) => {
            const existing = msg.agentMetadata ?? {};
            const prior = existing.browser ?? {};
            return {
              ...msg,
              agentMetadata: {
                ...existing,
                browser: {
                  ...prior,
                  total_duration_ms: data.total_duration_ms,
                  steps_completed: data.steps_completed,
                },
              },
            };
          });
          break;
        }

        case BrowserMessageType.ERROR: {
          // Req 4.11 / Req 17 — render error chip on current assistant msg.
          devWarn('ERROR frame:', data);
          updateCurrentAssistant((msg) => ({
            ...msg,
            isError: true,
            recoverable: data.recoverable,
            content: msg.content
              ? `${msg.content}\n\n${data.content}`
              : data.content,
            isStreaming: false,
          }));
          break;
        }

        // ─── Browser-specific frames ───────────────────────────────────

        case BrowserMessageType.BROWSER_SESSION_STARTED: {
          // Req 5.1.
          updateBrowserSession((prev) => ({
            ...prev,
            isActive: true,
            liveViewUrl: data.liveViewUrl,
          }));
          break;
        }

        case BrowserMessageType.BROWSER_ACTION_START: {
          // Req 5.2 — append running action entry keyed by stepNumber.
          const entry: BrowserActionEntry = {
            stepNumber: data.stepNumber,
            actionType: data.actionType,
            details: data.details,
            status: 'running',
          };
          updateCurrentAssistant((msg) => ({
            ...msg,
            actions: [...(msg.actions ?? []), entry],
          }));
          updateBrowserSession((prev) => ({
            ...prev,
            stepCounter: Math.max(prev.stepCounter, data.stepNumber),
          }));
          break;
        }

        case BrowserMessageType.BROWSER_ACTION_COMPLETE: {
          // Req 5.3 / 5.4 / 5.7 — match on stepNumber, tolerate out-of-order.
          const completeStatus: BrowserActionEntry['status'] = data.success
            ? 'succeeded'
            : 'failed';
          updateCurrentAssistant((msg) => {
            const actions = msg.actions ?? [];
            const idx = actions.findIndex((a) => a.stepNumber === data.stepNumber);
            if (idx === -1) {
              // COMPLETE arrived before START — synthesize a terminal entry so
              // the UI still records the step.
              return {
                ...msg,
                actions: [
                  ...actions,
                  {
                    stepNumber: data.stepNumber,
                    actionType: data.actionType,
                    details: '',
                    status: completeStatus,
                    result: data.result,
                  },
                ],
              };
            }
            const next = [...actions];
            next[idx] = {
              ...next[idx],
              status: completeStatus,
              result: data.result,
            };
            return { ...msg, actions: next };
          });
          break;
        }

        case BrowserMessageType.BROWSER_SCREENSHOT: {
          // Req 6.1 — append screenshot entry to current assistant message.
          const shot: BrowserScreenshotEntry = {
            stepNumber: data.stepNumber,
            screenshotUrl: data.screenshotUrl,
            screenshotPath: data.screenshotPath,
            title: data.title,
            timestamp: data.timestamp,
          };
          updateCurrentAssistant((msg) => ({
            ...msg,
            screenshots: [...(msg.screenshots ?? []), shot],
          }));
          updateBrowserSession((prev) => ({
            ...prev,
            stepCounter: Math.max(prev.stepCounter, data.stepNumber),
          }));
          break;
        }

        case BrowserMessageType.BROWSER_HITL_PROMPT: {
          // Req 8.1 / 8.2 — new assistant message carrying the prompt; set
          // pendingHitl to that entry reference.
          const hitl: BrowserHitlPromptEntry = {
            promptId: data.promptId,
            question: data.question,
            options: data.options,
            context: data.context,
            screenshotBase64: data.screenshotBase64 || undefined,
            status: 'pending',
          };
          const hitlMessage: BrowserChatMessage = {
            id: generateMessageId(),
            role: 'assistant',
            content: '',
            timestamp: now(),
            hitlPrompt: hitl,
          };
          updateMessages((prev) => [...prev, hitlMessage]);
          updateBrowserSession((prev) => ({ ...prev, pendingHitl: hitl }));
          break;
        }

        case BrowserMessageType.BROWSER_HITL_TIMEOUT: {
          // Req 8.4 — mark matching hitlPrompt as timeout, clear pendingHitl.
          updateMessages((prev) => {
            // Find the most recent assistant message carrying a pending hitlPrompt.
            for (let i = prev.length - 1; i >= 0; i--) {
              const m = prev[i];
              if (m.hitlPrompt && m.hitlPrompt.status === 'pending') {
                const next = [...prev];
                next[i] = {
                  ...m,
                  hitlPrompt: { ...m.hitlPrompt, status: 'timeout' },
                };
                return next;
              }
            }
            return prev;
          });
          updateBrowserSession((prev) => ({ ...prev, pendingHitl: null }));
          break;
        }

        case BrowserMessageType.BROWSER_LIVE_VIEW_URL: {
          // Req 5.6 — update liveViewUrl.
          updateBrowserSession((prev) => ({
            ...prev,
            liveViewUrl: data.liveViewUrl,
          }));
          break;
        }

        case BrowserMessageType.BROWSER_SESSION_ENDED: {
          // Req 5.5 — reset to initial.
          updateBrowserSession(() => INITIAL_BROWSER_SESSION);
          break;
        }

        default:
          // Exhaustiveness fallthrough — unknown types are ignored.
          break;
      }
    },
    [updateMessages, updateBrowserSession, updateCurrentAssistant, wsSend],
  );

  // ---- Reconnection with exponential backoff (Req 15) ----

  const scheduleReconnect = useCallback(() => {
    if (retryCountRef.current >= MAX_RETRIES) {
      setConnectionState('error');
      return;
    }
    const delay = Math.min(BASE_DELAY_MS * 2 ** retryCountRef.current, MAX_DELAY_MS);
    retryCountRef.current += 1;
    setConnectionState('connecting');

    reconnectTimerRef.current = setTimeout(() => {
      if (tokenRef.current && profileRef.current) {
        connectInternalRef.current(tokenRef.current, profileRef.current);
      }
    }, delay);
  }, []);

  // ---- Core WebSocket setup (internal) ----

  const connectInternal = useCallback(
    (token: string, profile: string) => {
      // Tear down any existing socket first.
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onmessage = null;
        wsRef.current.onerror = null;
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }

      const url = buildWebSocketUrl(token, profile);
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setConnectionState('connecting');

      ws.onopen = () => {
        // Req 3.1 / 2.2 — send CONNECTION_INIT; reset retry counter on open.
        retryCountRef.current = 0;
        wsSend({ type: BrowserMessageType.CONNECTION_INIT });
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data as string) as BrowserServerMessage;
          handleServerMessage(data);
        } catch (e) {
          // Req 17.4 — swallow malformed JSON; dev-mode log only; state unchanged.
          devWarn('Malformed WS frame:', e);
        }
      };

      ws.onerror = () => {
        // onerror is always followed by onclose — reconnection is handled there.
        devWarn('WebSocket error event');
      };

      ws.onclose = (event: CloseEvent) => {
        wsRef.current = null;
        setIsStreaming(false);

        if (isUserDisconnectRef.current) {
          // Req 16.3 — user-initiated disconnect; stay disconnected.
          setConnectionState('disconnected');
          isUserDisconnectRef.current = false;
        } else if (event.code !== 1000) {
          // Req 15.1 — abnormal closure; schedule backoff reconnect.
          scheduleReconnect();
        } else {
          setConnectionState('disconnected');
        }
      };
    },
    [wsSend, handleServerMessage, scheduleReconnect],
  );

  // Keep ref in sync so scheduleReconnect always calls the latest version.
  connectInternalRef.current = connectInternal;

  // ---- Public API ----

  /** Open a WebSocket connection with the given OIDC token and profile. */
  const connect = useCallback(
    (token: string, profile: string) => {
      tokenRef.current = token;
      profileRef.current = profile;
      retryCountRef.current = 0;
      isUserDisconnectRef.current = false;
      connectInternal(token, profile);
    },
    [connectInternal],
  );

  /** Gracefully close the WebSocket connection (close code 1000). */
  const disconnect = useCallback(() => {
    isUserDisconnectRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect');
    } else {
      setConnectionState('disconnected');
    }
  }, []);

  /**
   * Send a chat message to the backend — or, if a HITL prompt is pending,
   * dispatch BROWSER_HITL_RESPONSE instead (Req 3.2 / 3.3 / 8.3).
   */
  const sendMessage = useCallback(
    (content: string) => {
      const pending = pendingHitlRef.current;
      if (pending) {
        // HITL auto-swap — dispatch BROWSER_HITL_RESPONSE and clear pendingHitl.
        wsSend({
          type: BrowserMessageType.BROWSER_HITL_RESPONSE,
          promptId: pending.promptId,
          action: 'respond',
          value: content,
        });
        // Append user message reflecting their response; mark prompt as responded.
        const userMsg: BrowserChatMessage = {
          id: generateMessageId(),
          role: 'user',
          content,
          timestamp: now(),
        };
        updateMessages((prev) => {
          const withUser = [...prev, userMsg];
          // Mark matching hitlPrompt as responded.
          for (let i = withUser.length - 1; i >= 0; i--) {
            const m = withUser[i];
            if (m.hitlPrompt && m.hitlPrompt.promptId === pending.promptId) {
              withUser[i] = {
                ...m,
                hitlPrompt: { ...m.hitlPrompt, status: 'responded' },
              };
              break;
            }
          }
          return withUser;
        });
        updateBrowserSession((prev) => ({ ...prev, pendingHitl: null }));
        return;
      }

      // Normal chat flow — append user msg + streaming assistant placeholder,
      // then dispatch CHAT_MESSAGE.
      const userMsg: BrowserChatMessage = {
        id: generateMessageId(),
        role: 'user',
        content,
        timestamp: now(),
      };
      const assistantMsg: BrowserChatMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: '',
        timestamp: now(),
        isStreaming: true,
      };
      updateMessages((prev) => [...prev, userMsg, assistantMsg]);

      wsSend({ type: BrowserMessageType.CHAT_MESSAGE, content });
    },
    [wsSend, updateMessages, updateBrowserSession],
  );

  /** Dispatch a HITL response with an explicit action (e.g. option pick). */
  const sendHitlResponse = useCallback(
    (action: string, value?: string) => {
      const pending = pendingHitlRef.current;
      if (!pending) return;
      wsSend({
        type: BrowserMessageType.BROWSER_HITL_RESPONSE,
        promptId: pending.promptId,
        action,
        value,
      });
      updateMessages((prev) => {
        for (let i = prev.length - 1; i >= 0; i--) {
          const m = prev[i];
          if (m.hitlPrompt && m.hitlPrompt.promptId === pending.promptId) {
            const next = [...prev];
            next[i] = {
              ...m,
              hitlPrompt: { ...m.hitlPrompt, status: 'responded' },
            };
            return next;
          }
        }
        return prev;
      });
      updateBrowserSession((prev) => ({ ...prev, pendingHitl: null }));
    },
    [wsSend, updateMessages, updateBrowserSession],
  );

  /** Request mid-automation termination via BROWSER_STOP. */
  const stopBrowser = useCallback(() => {
    wsSend({ type: BrowserMessageType.BROWSER_STOP });
  }, [wsSend]);

  /** Request a fresh pre-signed DCV live-view URL. */
  const requestLiveViewUrl = useCallback(() => {
    wsSend({ type: BrowserMessageType.BROWSER_LIVE_VIEW_REQUEST });
  }, [wsSend]);

  /** Request a new session on the current connection. */
  const newSession = useCallback(() => {
    wsSend({ type: BrowserMessageType.NEW_SESSION });
  }, [wsSend]);

  /** Resume a previous session by ID. */
  const resumeSession = useCallback(
    (id: string) => {
      wsSend({ type: BrowserMessageType.RESUME_SESSION, session_id: id });
    },
    [wsSend],
  );

  /** Request the list of previous sessions. */
  const getSessions = useCallback(() => {
    wsSend({ type: BrowserMessageType.GET_SESSIONS });
  }, [wsSend]);

  /** Delete a session by ID. */
  const deleteSession = useCallback(
    (id: string) => {
      wsSend({ type: BrowserMessageType.DELETE_SESSION, session_id: id });
    },
    [wsSend],
  );

  // ---- Cleanup on unmount ----

  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on unmount.
        wsRef.current.close();
      }
    };
  }, []);

  return {
    connectionState,
    sessionId,
    messages,
    sessions,
    isStreaming,
    browserSession,
    sendMessage,
    sendHitlResponse,
    stopBrowser,
    requestLiveViewUrl,
    newSession,
    resumeSession,
    deleteSession,
    getSessions,
    connect,
    disconnect,
  };
};

export default useBrowserChatSession;
