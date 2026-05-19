"""
Full meeting processing pipeline:
  audio → transcribe → diarize → analyse → graph + memory → persist
"""
import json
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.services.meeting.analysis import analyse_transcript
from app.services.meeting.diarization import assign_speakers, merge_speaker_turns
from app.services.meeting.transcription import transcribe


async def process_meeting(
    meeting_id: uuid.UUID,
    file_path: str,
    db: AsyncSession,
) -> None:
    try:
        # 1. Transcribe
        trans = await transcribe(file_path)
        transcript: str = trans["transcript"]
        segments: list[dict] = trans["segments"]
        duration: float = trans["duration"]

        # 2. Speaker diarization
        diarized = assign_speakers(segments)
        turns = merge_speaker_turns(diarized)

        # 3. LLM analysis
        analysis = await analyse_transcript(transcript)

        # 4. Persist unresolved decisions + blockers in Redis
        await _track_unresolved(str(meeting_id), analysis["decisions"], analysis["blockers"])

        # 5. Update knowledge graph from meeting entities
        await _update_graph(str(meeting_id), transcript)

        # 6. Save to episodic memory
        await _save_memory(transcript, analysis)

        # 7. Write results to DB
        await db.execute(
            update(Meeting)
            .where(Meeting.id == meeting_id)
            .values(
                status="ready",
                duration_seconds=duration,
                transcript=transcript,
                speakers=turns,
                topics=analysis["topics"],
                action_items=analysis["action_items"],
                decisions=analysis["decisions"],
                blockers=analysis["blockers"],
            )
        )
        await db.commit()

    except Exception as e:
        await db.execute(
            update(Meeting)
            .where(Meeting.id == meeting_id)
            .values(status="error", error_message=str(e))
        )
        await db.commit()
        raise


async def _track_unresolved(meeting_id: str, decisions: list[dict], blockers: list[dict]) -> None:
    try:
        from app.database import redis_client
        import time
        if not redis_client:
            return
        ts = time.time()
        for d in decisions:
            entry = json.dumps({"meeting_id": meeting_id, "decision": d.get("decision", ""), "ts": ts})
            await redis_client.zadd("meeting:decisions:unresolved", {entry: ts})
        for b in blockers:
            entry = json.dumps({"meeting_id": meeting_id, "issue": b.get("issue", ""), "blocks": b.get("blocks", ""), "ts": ts})
            await redis_client.zadd("meeting:blockers:unresolved", {entry: ts})
        # 30-day TTL
        await redis_client.expire("meeting:decisions:unresolved", 86400 * 30)
        await redis_client.expire("meeting:blockers:unresolved", 86400 * 30)
    except Exception:
        pass


async def _update_graph(meeting_id: str, transcript: str) -> None:
    try:
        from app.database import neo4j_driver
        from app.services.knowledge_graph.extractor import extract_from_chunk
        from app.services.knowledge_graph.ingestion import ingest
        from app.services.knowledge_graph.schema import ensure_schema
        if not neo4j_driver:
            return
        await ensure_schema(neo4j_driver)
        extraction = await extract_from_chunk(transcript[:2000])
        await ingest(f"meeting:{meeting_id}", f"Meeting {meeting_id[:8]}", extraction, neo4j_driver)
    except Exception:
        pass


async def _save_memory(transcript: str, analysis: dict) -> None:
    try:
        from app.services.memory.episodic import record
        summary = f"Meeting topics: {', '.join(analysis['topics'])}. " \
                  f"{len(analysis['action_items'])} action items. " \
                  f"{len(analysis['decisions'])} decisions. " \
                  f"{len(analysis['blockers'])} blockers."
        await record(f"Meeting transcript ({len(transcript)} chars)", summary)
    except Exception:
        pass
