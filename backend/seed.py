"""
TutorForge AI — Demo Data Seeder
Seeds a realistic Computer Networks course so the app looks excellent immediately.
All demo data is flagged with is_demo=True for clear provenance.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from database import (
    AsyncSessionLocal, Source, SourceChunk, Concept, ConceptRelationship,
    Question, Mastery, MasteryHistory, Assessment, AssessmentResponse,
    ChatSession, ChatMessage, StudySession
)
from vector_store import vector_store

logger = logging.getLogger(__name__)

STUDENT_ID = "default_student"


DEMO_CONCEPTS = [
    # (name, description, parent_name, subject)
    ("Computer Networks", "Fundamentals of computer networking including protocols, layers, and data communication.", None, "Computer Networks"),
    ("Transport Layer", "Protocols that provide end-to-end communication services: TCP and UDP.", "Computer Networks", "Computer Networks"),
    ("TCP", "Transmission Control Protocol — reliable, ordered, connection-oriented transport.", "Transport Layer", "Computer Networks"),
    ("UDP", "User Datagram Protocol — lightweight, connectionless transport for real-time applications.", "Transport Layer", "Computer Networks"),
    ("Flow Control", "TCP mechanism to prevent sender from overwhelming a slow receiver via receive window.", "TCP", "Computer Networks"),
    ("Congestion Control", "TCP algorithms to prevent network overload: Slow Start, Congestion Avoidance, Fast Retransmit, Fast Recovery.", "TCP", "Computer Networks"),
    ("Sliding Window", "Protocol mechanism for efficient data transmission with multiple unacknowledged frames in flight.", "Flow Control", "Computer Networks"),
    ("Retransmission", "TCP mechanism to recover lost segments via timeout or duplicate ACK detection.", "TCP", "Computer Networks"),
    ("Network Layer", "Responsible for logical addressing and routing: IP protocol, routing algorithms.", "Computer Networks", "Computer Networks"),
    ("IP Protocol", "Internet Protocol providing logical addressing and packet forwarding across networks.", "Network Layer", "Computer Networks"),
    ("Routing Algorithms", "Algorithms for determining optimal paths through the network: Dijkstra, Bellman-Ford.", "Network Layer", "Computer Networks"),
    ("Data Link Layer", "Provides node-to-node data transfer, error detection, and MAC addressing.", "Computer Networks", "Computer Networks"),
]

DEMO_QUESTIONS = [
    {
        "concept": "Congestion Control",
        "type": "mcq",
        "difficulty": 2,
        "text": "In TCP Slow Start, how does the congestion window (cwnd) grow?",
        "options": [
            "A) Linearly by 1 MSS per RTT",
            "B) Exponentially by doubling each RTT",
            "C) Remains constant until a timeout",
            "D) Grows based on receiver window size only"
        ],
        "correct": "B) Exponentially by doubling each RTT",
        "explanation": "In Slow Start, cwnd doubles every round-trip time (exponential growth) until it reaches ssthresh or a loss event occurs."
    },
    {
        "concept": "Congestion Control",
        "type": "mcq",
        "difficulty": 3,
        "text": "After TCP Fast Retransmit, the congestion window (cwnd) is set to:",
        "options": [
            "A) 1 MSS (restart slow start)",
            "B) ssthresh (enter congestion avoidance)",
            "C) ssthresh/2 and slow start restarts",
            "D) cwnd/2 and enter fast recovery"
        ],
        "correct": "D) cwnd/2 and enter fast recovery",
        "explanation": "Fast Recovery sets cwnd = ssthresh = cwnd/2 and inflates cwnd for each duplicate ACK received, remaining in Fast Recovery until a new ACK arrives."
    },
    {
        "concept": "Congestion Control",
        "type": "mcq",
        "difficulty": 1,
        "text": "Which event triggers TCP Fast Retransmit?",
        "options": [
            "A) A single duplicate ACK",
            "B) Three duplicate ACKs",
            "C) A retransmission timeout",
            "D) The receive window reaching zero"
        ],
        "correct": "B) Three duplicate ACKs",
        "explanation": "Three duplicate ACKs indicate a missing segment without full network congestion. TCP performs Fast Retransmit to recover quickly without waiting for a timeout."
    },
    {
        "concept": "Flow Control",
        "type": "mcq",
        "difficulty": 2,
        "text": "TCP flow control is implemented using:",
        "options": [
            "A) The congestion window (cwnd) only",
            "B) The receive window (rwnd) advertised by the receiver",
            "C) Time-to-live field in IP headers",
            "D) Sequence numbers in the TCP header"
        ],
        "correct": "B) The receive window (rwnd) advertised by the receiver",
        "explanation": "The receiver advertises its available buffer space as rwnd. The sender limits unacknowledged data to min(cwnd, rwnd) to prevent overwhelming the receiver."
    },
    {
        "concept": "UDP",
        "type": "mcq",
        "difficulty": 1,
        "text": "Which of the following applications would most likely use UDP instead of TCP?",
        "options": [
            "A) File download",
            "B) Web page retrieval",
            "C) Live video streaming",
            "D) Email delivery"
        ],
        "correct": "C) Live video streaming",
        "explanation": "Live video streaming prioritizes low latency over perfect reliability. UDP's lack of retransmission overhead makes it suitable, as occasional packet loss is preferable to delays."
    },
    {
        "concept": "Sliding Window",
        "type": "mcq",
        "difficulty": 2,
        "text": "What does the Sliding Window protocol allow the sender to do?",
        "options": [
            "A) Send only one packet at a time",
            "B) Send multiple packets before requiring an acknowledgement",
            "C) Encrypt data before transmission",
            "D) Select the best routing path"
        ],
        "correct": "B) Send multiple packets before requiring an acknowledgement",
        "explanation": "The sliding window allows a sender to have multiple unacknowledged frames in transit simultaneously, improving throughput by keeping the network pipe full."
    },
    {
        "concept": "TCP",
        "type": "true_false",
        "difficulty": 1,
        "text": "TCP guarantees in-order delivery of data segments.",
        "options": ["True", "False"],
        "correct": "True",
        "explanation": "TCP reorders segments at the receiver using sequence numbers, guaranteeing that the application receives data in the same order it was sent."
    },
    {
        "concept": "Retransmission",
        "type": "mcq",
        "difficulty": 2,
        "text": "What is the purpose of TCP's retransmission timeout (RTO)?",
        "options": [
            "A) To limit the maximum segment size",
            "B) To trigger retransmission when an ACK is not received in time",
            "C) To control the receive window size",
            "D) To establish a new connection after data loss"
        ],
        "correct": "B) To trigger retransmission when an ACK is not received in time",
        "explanation": "If an ACK for a sent segment is not received before the RTO expires, TCP assumes the segment was lost and retransmits it."
    },
]

DEMO_CHUNKS = [
    {
        "source_name": "Computer Networks — Lecture 05",
        "source_type": "video",
        "content": "TCP congestion control is implemented through four interrelated algorithms: Slow Start, Congestion Avoidance, Fast Retransmit, and Fast Recovery. The congestion window (cwnd) controls how much data can be in transit. During Slow Start, cwnd begins at 1 MSS and doubles every RTT until it reaches the slow start threshold (ssthresh).",
        "timestamp_start": 760.0,
        "timestamp_end": 818.0,
        "section_title": "12:40–13:38",
    },
    {
        "source_name": "Computer Networks — Lecture 05",
        "source_type": "video",
        "content": "Once cwnd reaches ssthresh, TCP enters Congestion Avoidance where cwnd grows linearly by 1 MSS per RTT. When packet loss is detected by three duplicate ACKs, TCP performs Fast Retransmit: retransmitting the missing segment immediately and entering Fast Recovery. cwnd is set to ssthresh = cwnd/2.",
        "timestamp_start": 818.0,
        "timestamp_end": 895.0,
        "section_title": "13:38–14:55",
    },
    {
        "source_name": "Computer Networks — Lecture 05",
        "source_type": "video",
        "content": "Flow control prevents the sender from overwhelming the receiver's buffer. TCP implements this using the receive window (rwnd) field in the TCP header. The receiver advertises rwnd — the available buffer space. The sender ensures that unacknowledged data does not exceed min(cwnd, rwnd).",
        "timestamp_start": 1120.0,
        "timestamp_end": 1175.0,
        "section_title": "18:40–19:35",
    },
    {
        "source_name": "Computer Networks Textbook",
        "source_type": "pdf",
        "content": "The sliding window protocol allows a sender to have multiple unacknowledged frames in transit simultaneously. The window size W determines how many frames can be sent before an acknowledgement is required. As acknowledgements arrive, the window slides forward, allowing new frames to be sent. This fills the network pipe and dramatically improves throughput over stop-and-wait protocols.",
        "page_number": 87,
        "section_title": "Chapter 4: Transport Layer",
    },
    {
        "source_name": "Computer Networks Textbook",
        "source_type": "pdf",
        "content": "UDP (User Datagram Protocol) is a connectionless transport layer protocol. Unlike TCP, UDP provides no guarantees of delivery, ordering, or error correction. The UDP header is only 8 bytes: source port, destination port, length, and checksum. Applications that require low latency and can tolerate some loss — such as DNS, VoIP, and video streaming — use UDP.",
        "page_number": 72,
        "section_title": "Chapter 3: Transport Layer — UDP",
    },
    {
        "source_name": "Computer Networks Textbook",
        "source_type": "pdf",
        "content": "TCP's three-way handshake establishes a connection: (1) Client sends SYN with initial sequence number x, (2) Server responds with SYN-ACK acknowledging x+1 and providing its initial sequence number y, (3) Client sends ACK acknowledging y+1. After the handshake, data transfer can begin. Connection teardown uses a four-way FIN exchange.",
        "page_number": 78,
        "section_title": "Chapter 4: TCP Connection Management",
    },
    {
        "source_name": "Transport Layer Slides",
        "source_type": "pptx",
        "content": "TCP Congestion Control Summary: Slow Start → exponential growth. Congestion Avoidance → linear growth. Fast Retransmit → 3 dup ACKs trigger immediate retransmission. Fast Recovery → cwnd = ssthresh, then linear growth. Timeout → ssthresh = cwnd/2, cwnd = 1 MSS, restart Slow Start.",
        "slide_number": 14,
        "section_title": "Slide 14: TCP Congestion Control",
    },
    {
        "source_name": "Transport Layer Slides",
        "source_type": "pptx",
        "content": "Retransmission Timeout (RTO): TCP sets a timer for each segment sent. If an ACK is not received before the RTO expires, the segment is retransmitted. RTO is calculated using the Exponential Weighted Moving Average (EWMA) of the sample RTT. RTO = EstimatedRTT + 4 × DevRTT.",
        "slide_number": 11,
        "section_title": "Slide 11: Retransmission",
    },
]

# Mastery seeds: (concept_name, score)
DEMO_MASTERIES = [
    ("TCP", 0.72),
    ("UDP", 0.91),
    ("Congestion Control", 0.48),
    ("Flow Control", 0.67),
    ("Sliding Window", 0.61),
    ("Retransmission", 0.55),
    ("Network Layer", 0.38),
    ("IP Protocol", 0.43),
]


async def seed_demo_data():
    """Seed demo data if database is empty.
    
    Also re-populates the vector store from DB chunks on every startup,
    since the in-memory vector store loses data on restart (even when
    a persist path is configured, this is a safe idempotent resync).
    """
    async with AsyncSessionLocal() as db:
        # Check if already seeded in DB
        result = await db.execute(select(Concept).where(Concept.is_demo == True))
        existing = result.scalars().first()

        if existing:
            logger.info("Demo data already seeded in DB — checking vector store...")
            # Re-sync vector store from DB if it is empty
            await _resync_vector_store_if_empty(db)
            return

        logger.info("Seeding demo data...")

        try:
            await _seed_concepts(db)
            await _seed_sources_and_chunks(db)
            await _seed_questions(db)
            await _seed_masteries(db)
            await _seed_study_sessions(db)
            await db.commit()
            logger.info("Demo data seeded successfully")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to seed demo data: {e}")
            raise


async def _resync_vector_store_if_empty(db):
    """Re-index DB chunks into vector store when it is empty (e.g. after restart)."""
    try:
        count = vector_store.count()
        if count > 0:
            logger.info(f"Vector store already has {count} chunks — skipping resync")
            return

        logger.info("Vector store is empty — resyncing from DB chunks...")
        result = await db.execute(select(SourceChunk))
        chunks = result.scalars().all()

        if not chunks:
            logger.warning("No chunks in DB to resync")
            return

        texts = []
        metadatas = []
        ids = []

        # Get source info for metadata
        src_result = await db.execute(select(Source))
        sources = {s.id: s for s in src_result.scalars().all()}

        for chunk in chunks:
            src = sources.get(chunk.source_id)
            meta = {
                "source_id": chunk.source_id,
                "source_name": src.name if src else "Unknown",
                "source_type": src.source_type if src else "unknown",
                "page_number": chunk.page_number,
                "slide_number": chunk.slide_number,
                "timestamp_start": chunk.timestamp_start,
                "timestamp_end": chunk.timestamp_end,
            }
            chroma_id = chunk.chroma_id or str(uuid.uuid4())
            texts.append(chunk.content)
            metadatas.append(meta)
            ids.append(chroma_id)

        vector_store.add_chunks(texts, metadatas, ids)
        logger.info(f"Vector store resynced: {len(texts)} chunks indexed")
    except Exception as e:
        logger.error(f"Vector store resync failed: {e}")


async def _seed_concepts(db):
    """Seed concept hierarchy."""
    concept_map = {}

    for name, desc, parent_name, subject in DEMO_CONCEPTS:
        parent_id = concept_map.get(parent_name) if parent_name else None
        c = Concept(
            name=name,
            description=desc,
            parent_id=parent_id,
            subject=subject,
            is_demo=True
        )
        db.add(c)
        await db.flush()
        concept_map[name] = c.id

    # Add relationships
    relationships = [
        ("TCP", "Flow Control", "contains"),
        ("TCP", "Congestion Control", "contains"),
        ("TCP", "Retransmission", "contains"),
        ("Flow Control", "Sliding Window", "contains"),
        ("Congestion Control", "Sliding Window", "relates_to"),
        ("TCP", "UDP", "relates_to"),
    ]
    for src_name, tgt_name, rel_type in relationships:
        src_id = concept_map.get(src_name)
        tgt_id = concept_map.get(tgt_name)
        if src_id and tgt_id:
            r = ConceptRelationship(
                source_concept_id=src_id,
                target_concept_id=tgt_id,
                relationship_type=rel_type
            )
            db.add(r)

    await db.flush()
    logger.info(f"Seeded {len(DEMO_CONCEPTS)} concepts")
    return concept_map


async def _seed_sources_and_chunks(db):
    """Seed demo sources and embed chunks into vector store."""
    source_map = {}

    demo_sources = [
        ("Computer Networks — Lecture 05", "lecture_05_transport_layer.mp4", "video"),
        ("Computer Networks Textbook", "computer_networks_textbook.pdf", "pdf"),
        ("Transport Layer Slides", "transport_layer_slides.pptx", "pptx"),
    ]

    for name, filename, stype in demo_sources:
        s = Source(
            name=name,
            original_filename=filename,
            source_type=stype,
            file_path=None,
            file_size=0,
            status="processed",
            is_demo=True
        )
        db.add(s)
        await db.flush()
        source_map[name] = s.id

    await db.flush()

    # Seed chunks
    texts = []
    metadatas = []
    ids = []
    db_chunks = []

    for idx, chunk_data in enumerate(DEMO_CHUNKS):
        source_name = chunk_data["source_name"]
        source_id = source_map.get(source_name)
        if not source_id:
            continue

        chroma_id = str(uuid.uuid4())
        meta = {
            "source_id": source_id,
            "source_name": source_name,
            "source_type": chunk_data["source_type"],
            "page_number": chunk_data.get("page_number"),
            "slide_number": chunk_data.get("slide_number"),
            "timestamp_start": chunk_data.get("timestamp_start"),
            "timestamp_end": chunk_data.get("timestamp_end"),
        }

        db_chunk = SourceChunk(
            source_id=source_id,
            chunk_index=idx,
            content=chunk_data["content"],
            page_number=chunk_data.get("page_number"),
            slide_number=chunk_data.get("slide_number"),
            timestamp_start=chunk_data.get("timestamp_start"),
            timestamp_end=chunk_data.get("timestamp_end"),
            section_title=chunk_data.get("section_title"),
            chroma_id=chroma_id,
            metadata_=meta
        )
        db_chunks.append(db_chunk)
        texts.append(chunk_data["content"])
        metadatas.append(meta)
        ids.append(chroma_id)

    db.add_all(db_chunks)
    await db.flush()

    # Index in vector store
    try:
        vector_store.add_chunks(texts, metadatas, ids)
        logger.info(f"Indexed {len(texts)} demo chunks in vector store")
    except Exception as e:
        logger.warning(f"Vector store indexing failed (will work without it): {e}")

    logger.info(f"Seeded {len(demo_sources)} demo sources and {len(DEMO_CHUNKS)} chunks")


async def _seed_questions(db):
    """Seed demo quiz questions."""
    # Get concept map
    result = await db.execute(select(Concept).where(Concept.is_demo == True))
    concepts = {c.name: c.id for c in result.scalars().all()}

    for qdata in DEMO_QUESTIONS:
        cname = qdata["concept"]
        cid = concepts.get(cname)
        q = Question(
            concept_id=cid,
            question_type=qdata["type"],
            difficulty=qdata["difficulty"],
            text=qdata["text"],
            options=qdata["options"],
            correct_answer=qdata["correct"],
            explanation=qdata["explanation"],
            is_demo=True
        )
        db.add(q)

    await db.flush()
    logger.info(f"Seeded {len(DEMO_QUESTIONS)} demo questions")


async def _seed_masteries(db):
    """Seed realistic mastery scores for default student."""
    result = await db.execute(select(Concept).where(Concept.is_demo == True))
    concepts = {c.name: c.id for c in result.scalars().all()}

    now = datetime.utcnow()

    for cname, score in DEMO_MASTERIES:
        cid = concepts.get(cname)
        if not cid:
            continue

        questions_seen = int(10 + score * 20)
        correct = int(questions_seen * score)

        m = Mastery(
            student_id=STUDENT_ID,
            concept_id=cid,
            score=score,
            questions_seen=questions_seen,
            correct_answers=correct,
            last_updated=now
        )
        db.add(m)
        await db.flush()

        # Add history over last 7 days
        for day in range(7, 0, -1):
            variation = (7 - day) / 7 * 0.15
            h_score = max(0.0, min(1.0, score - 0.15 + variation))
            h = MasteryHistory(
                mastery_id=m.id,
                score=h_score,
                recorded_at=now - timedelta(days=day)
            )
            db.add(h)

    await db.flush()
    logger.info(f"Seeded mastery data for {len(DEMO_MASTERIES)} concepts")


async def _seed_study_sessions(db):
    """Seed realistic study session history."""
    now = datetime.utcnow()
    sessions = [
        (7, 35, "quiz"),
        (6, 22, "chat"),
        (5, 45, "review"),
        (4, 18, "quiz"),
        (3, 30, "chat"),
        (2, 25, "quiz"),
        (1, 40, "review"),
        (0, 20, "quiz"),
    ]

    for days_ago, duration, activity in sessions:
        started = now - timedelta(days=days_ago, hours=2)
        s = StudySession(
            student_id=STUDENT_ID,
            started_at=started,
            ended_at=started + timedelta(minutes=duration),
            duration_minutes=float(duration),
            activity_type=activity
        )
        db.add(s)

    await db.flush()
    logger.info("Seeded study session history")

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_demo_data())
