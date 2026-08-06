# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Test WebSocket connection to locally running Docker container on port 8080."""

import asyncio
import json
import time

import websockets

WS_URL = "ws://localhost:8080/ws"


async def run():
    ws = await websockets.connect(WS_URL, open_timeout=60, ping_interval=None)
    await ws.send(json.dumps({"type": "CONNECTION_INIT"}))

    start = time.time()
    frame_count = 0
    last_frame_time = start

    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=300)
                frame = json.loads(raw)
                frame_count += 1
                now = time.time()
                gap = now - last_frame_time
                elapsed = now - start
                ftype = frame.get("type", "?")
                extra = ""
                if ftype == "BROWSER_SCREENSHOT":
                    extra = " [has image]"
                elif ftype == "METADATA":
                    extra = " [metadata]"
                print(f"[{elapsed:.1f}s] (+{gap:.1f}s) Frame #{frame_count}: {ftype}{extra}")
                last_frame_time = now

                if ftype == "CONNECTION_ESTABLISHED":
                    await ws.send(json.dumps({
                        "type": "CHAT_MESSAGE",
                        "content": (
                            "Navigate to https://en.wikipedia.org. "
                            "Type Amazon Company in the search field. "
                            "Hit the Search button."
                        ),
                        "session_id": frame["session_id"],
                    }))
                    print(f"[{elapsed:.1f}s] Sent CHAT_MESSAGE")

                if ftype == "ORCHESTRATION_END":
                    print(f"DONE after {elapsed:.1f}s, {frame_count} frames")
                    break
            except asyncio.TimeoutError:
                print(f"Timeout after {time.time()-start:.1f}s")
                break
    except websockets.exceptions.ConnectionClosedError as e:
        elapsed = time.time() - start
        print(f"CONNECTION DROPPED at {elapsed:.1f}s after {frame_count} frames: {e}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"ERROR at {elapsed:.1f}s: {type(e).__name__}: {e}")
    finally:
        await ws.close()


if __name__ == "__main__":
    asyncio.run(run())
