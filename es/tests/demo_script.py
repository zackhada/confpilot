"""The demo conversation from docs/CONFPILOT_PLAN.md, used as search and recap test data."""

from __future__ import annotations

import uuid

from confpilot_es import EsStore

CLAYTON = {"user_id": "user-clayton", "name": "Clayton"}
ZACK = {"user_id": "user-zack", "name": "Zack"}
BASE_SPOKEN_AT = 1_794_000_000_000
RAG_LINE = "I work at Elasticsearch, we do managed hybrid search, including RAG and keyword search."
RRF_LINE = (
    "Great question! It uses BM25 for keyword matches, while the embeddings handle meaning, "
    "and RRF to rank the results to return to the user or agent."
)
SCRIPT: list[tuple[dict[str, str], str]] = [
    (CLAYTON, "I work at Radar, we do SRE for Kubernetes clusters. What do you do?"),
    (ZACK, RAG_LINE),
    (
        CLAYTON,
        "Nice! So that will help power apps' search engines, or what are customers trying to do with your technology?",
    ),
    (
        ZACK,
        "Yeah, for sure! Wikipedia is one of our customers. Nowadays, a lot of our customers are using "
        "our product to embed thousands of documents into a knowledge base the agent can pull from.",
    ),
    (
        CLAYTON,
        "Interesting, so those documents are turned into vectors that can be retrieved easily. How does "
        "your search service determine what is most relevant to the agent or user's query?",
    ),
    (ZACK, RRF_LINE),
    (CLAYTON, "Oh, makes sense! At Radar, we have some internal search service use cases. Can I get your LinkedIn?"),
]


async def index_demo_script(store: EsStore) -> str:
    """Percolate and index every line into a fresh room. Returns the room code."""
    room = f"demo-{uuid.uuid4().hex[:6]}"
    for position, (speaker, text) in enumerate(SCRIPT):
        await store.index_utterance(
            utterance_id=f"{room}-{position}",
            room=room,
            speaker=speaker,
            spoken_at=BASE_SPOKEN_AT + position * 8000,
            text=text,
            term_ids=await store.percolate(text),
        )
    return room
