"""
WebSocket endpoint for Amazon Transcribe Streaming.

Accepts raw PCM audio chunks from the browser (16kHz, 16-bit, mono)
via WebSocket, streams them to Amazon Transcribe, and relays interim
+ final transcript events back to the client as JSON.

The frontend's useVoiceSearch hook is the consumer: it captures mic
audio via Web Audio API, sends binary frames here, and receives
{ type: 'interim'|'final', text } events to fill the search bar.

Falls back gracefully when Transcribe is unavailable (missing IAM
permissions, SDK not installed, network error) — sends an error
event and closes the WebSocket cleanly.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# Audio config matching the frontend's AudioContext settings
SAMPLE_RATE = 16000
MEDIA_ENCODING = "pcm"
LANGUAGE_CODE = "en-US"
TRANSCRIBE_REGION = os.getenv("TRANSCRIBE_REGION", "us-east-1")


def transcribe_runtime_status() -> dict[str, str | bool]:
    """Return the active backend interpreter's voice-search readiness."""
    try:
        import amazon_transcribe  # noqa: F401

        sdk_available = True
    except ImportError:
        sdk_available = False
    return {
        "sdk_available": sdk_available,
        "python": sys.executable,
        "region": TRANSCRIBE_REGION,
    }


async def _transcribe_stream(
    audio_chunks: AsyncGenerator[bytes, None],
) -> AsyncGenerator[dict, None]:
    """Stream audio to Amazon Transcribe and yield transcript events.

    Uses the amazon-transcribe SDK if available, falls back to a
    boto3-based implementation otherwise.
    """
    try:
        from amazon_transcribe.client import TranscribeStreamingClient
        from amazon_transcribe.handlers import TranscriptResultStreamHandler
        from amazon_transcribe.model import TranscriptEvent

        client = TranscribeStreamingClient(region=TRANSCRIBE_REGION)

        stream = await client.start_stream_transcription(
            language_code=LANGUAGE_CODE,
            media_sample_rate_hz=SAMPLE_RATE,
            media_encoding=MEDIA_ENCODING,
        )

        # Queue for transcript events from the handler
        event_queue: asyncio.Queue[dict] = asyncio.Queue()

        class Handler(TranscriptResultStreamHandler):
            async def handle_transcript_event(self, transcript_event: TranscriptEvent):
                results = transcript_event.transcript.results
                for result in results:
                    if not result.alternatives:
                        continue
                    text = result.alternatives[0].transcript
                    if not text:
                        continue
                    event_type = "final" if not result.is_partial else "interim"
                    await event_queue.put({"type": event_type, "text": text})

        handler = Handler(stream.output_stream)

        # Task 1: feed audio chunks to Transcribe
        async def feed_audio():
            try:
                async for chunk in audio_chunks:
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                await stream.input_stream.end_stream()
            except Exception as exc:
                logger.warning("Transcribe audio feed error: %s", exc)

        # Task 2: handle transcript events
        handler_task = asyncio.create_task(handler.handle_events())
        feed_task = asyncio.create_task(feed_audio())

        # Yield events as they arrive, until both tasks complete
        while not handler_task.done() or not event_queue.empty():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                continue

        # Ensure tasks are cleaned up
        await asyncio.gather(handler_task, feed_task, return_exceptions=True)

    except ImportError:
        python_path = transcribe_runtime_status()["python"]
        logger.warning(
            "amazon-transcribe SDK not available in backend interpreter %s. "
            "Start the backend with pellier/backend/.venv/bin/python -m uvicorn or install the dependency there.",
            python_path,
        )
        yield {
            "type": "error",
            "text": (
                "Voice search requires amazon-transcribe in the backend Python "
                "environment. Start the backend with pellier/backend/.venv/bin/python -m uvicorn."
            ),
        }
    except Exception as exc:
        logger.exception("Transcribe streaming error: %s", exc)
        yield {
            "type": "error",
            "text": "Voice search is temporarily unavailable.",
            "code": "transcribe_unavailable",
        }


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """WebSocket endpoint for real-time voice transcription.

    Protocol:
      Client → Server: binary frames (PCM audio, 16kHz 16-bit mono)
      Server → Client: JSON text frames:
        { "type": "interim", "text": "a thoughtful" }
        { "type": "final",  "text": "a thoughtful gift for someone who runs" }
        { "type": "error",  "text": "..." }
        { "type": "done" }
    """
    await websocket.accept()
    logger.info("🎤 Transcribe WebSocket connected (region=%s)", TRANSCRIBE_REGION)

    # Async generator that yields audio chunks from the WebSocket
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def audio_generator() -> AsyncGenerator[bytes, None]:
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            yield chunk

    # Start the transcription pipeline
    transcript_gen = _transcribe_stream(audio_generator())

    async def relay_transcripts():
        """Forward transcript events to the WebSocket client."""
        try:
            async for event in transcript_gen:
                await websocket.send_json(event)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.warning("Transcript relay error: %s", exc)

    relay_task = asyncio.create_task(relay_transcripts())

    try:
        while True:
            # Receive binary audio frames from the browser
            data = await websocket.receive()
            if "bytes" in data and data["bytes"]:
                await audio_queue.put(data["bytes"])
            elif "text" in data:
                # Client can send a text "stop" command
                msg = data.get("text", "")
                if msg == "stop":
                    break
    except WebSocketDisconnect:
        logger.info("🎤 Transcribe WebSocket disconnected")
    except Exception as exc:
        logger.warning("Transcribe WebSocket error: %s", exc)
    finally:
        # Signal end of audio
        await audio_queue.put(None)
        # Wait for relay to finish
        try:
            await asyncio.wait_for(relay_task, timeout=5)
        except asyncio.TimeoutError:
            relay_task.cancel()
        # Send done event and close
        try:
            await websocket.send_json({"type": "done"})
            await websocket.close()
        except Exception:
            pass
        logger.info("🎤 Transcribe session ended")
