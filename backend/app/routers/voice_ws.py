"""
Voice AI WebSocket endpoint at /ws/voice.

Client → Server messages (JSON):
  {type: "audio_chunk", data: "<base64>", is_last: bool}
  {type: "barge_in"}
  {type: "ping"}

Server → Client messages (JSON):
  {type: "state",      state: "idle"|"listening"|"processing"|"speaking"}
  {type: "transcript", text: str}
  {type: "tone",       tone: str}
  {type: "agent_token",token: str}
  {type: "tts_chunk",  data: "<base64>"}
  {type: "tts_done"}
  {type: "error",      message: str}
  {type: "pong"}

State machine:
  idle → listening (on first audio_chunk)
  listening → processing (on is_last=true)
  processing → speaking (after full response built)
  speaking → idle (tts_done or barge_in)
"""
import asyncio
import base64
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.voice.stt import transcribe_bytes
from app.services.voice.tone import detect_tone
from app.services.voice.agent_bridge import stream_response
from app.services.voice.tts import synthesize_stream

router = APIRouter()
logger = logging.getLogger(__name__)

_SEND_TIMEOUT = 30.0  # seconds to wait for WebSocket send


async def _send(ws: WebSocket, data: dict):
    await asyncio.wait_for(ws.send_json(data), timeout=_SEND_TIMEOUT)


async def _set_state(ws: WebSocket, state: str):
    await _send(ws, {"type": "state", "state": state})


@router.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket):
    await websocket.accept()
    await _set_state(websocket, "idle")

    audio_chunks: list[bytes] = []
    tts_task: asyncio.Task | None = None
    barge_in_event = asyncio.Event()
    state = "idle"

    async def run_tts(text: str):
        nonlocal state
        barge_in_event.clear()
        await _set_state(websocket, "speaking")
        try:
            async for chunk in synthesize_stream(text):
                if barge_in_event.is_set():
                    break
                encoded = base64.b64encode(chunk).decode()
                await _send(websocket, {"type": "tts_chunk", "data": encoded})
        except Exception as e:
            logger.warning("TTS error: %s", e)
        finally:
            if not barge_in_event.is_set():
                await _send(websocket, {"type": "tts_done"})
            await _set_state(websocket, "idle")
            state = "idle"

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                import json
                msg = json.loads(raw)
            except Exception:
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await _send(websocket, {"type": "pong"})
                continue

            if msg_type == "barge_in":
                barge_in_event.set()
                if tts_task and not tts_task.done():
                    tts_task.cancel()
                audio_chunks.clear()
                state = "listening"
                await _set_state(websocket, "listening")
                continue

            if msg_type == "audio_chunk":
                raw_b64 = msg.get("data", "")
                is_last = bool(msg.get("is_last", False))

                try:
                    chunk_bytes = base64.b64decode(raw_b64)
                    audio_chunks.append(chunk_bytes)
                except Exception:
                    pass

                if state == "idle":
                    state = "listening"
                    await _set_state(websocket, "listening")

                if not is_last:
                    continue

                # All audio received — process
                state = "processing"
                await _set_state(websocket, "processing")

                combined = b"".join(audio_chunks)
                audio_chunks.clear()

                try:
                    transcript = await transcribe_bytes(combined)
                except Exception as e:
                    await _send(websocket, {"type": "error", "message": f"STT failed: {e}"})
                    state = "idle"
                    await _set_state(websocket, "idle")
                    continue

                if not transcript.strip():
                    await _send(websocket, {"type": "transcript", "text": ""})
                    state = "idle"
                    await _set_state(websocket, "idle")
                    continue

                await _send(websocket, {"type": "transcript", "text": transcript})

                # Tone detection (non-blocking, fire and forget)
                tone_task = asyncio.create_task(detect_tone(transcript))

                # Stream agent response, collect full text for TTS
                full_response_parts: list[str] = []
                try:
                    async for token in stream_response(transcript):
                        full_response_parts.append(token)
                        await _send(websocket, {"type": "agent_token", "token": token})
                except Exception as e:
                    await _send(websocket, {"type": "error", "message": f"Agent error: {e}"})
                    state = "idle"
                    await _set_state(websocket, "idle")
                    continue

                # Send tone result
                try:
                    tone = await asyncio.wait_for(tone_task, timeout=5.0)
                    await _send(websocket, {"type": "tone", "tone": tone})
                except Exception:
                    pass

                # TTS the full response
                full_response = "".join(full_response_parts).strip()
                if full_response:
                    tts_task = asyncio.create_task(run_tts(full_response))
                    await tts_task
                else:
                    state = "idle"
                    await _set_state(websocket, "idle")

    except WebSocketDisconnect:
        if tts_task and not tts_task.done():
            tts_task.cancel()
    except Exception as e:
        logger.error("Voice WS error: %s", e)
        try:
            await _send(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass
