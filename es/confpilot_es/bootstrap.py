"""Create the ConfPilot indices and load a glossary.

    python -m confpilot_es.bootstrap --glossary ../contracts/fixtures/glossary.sample.json [--recreate]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from confpilot_es.config import DEFAULT_PREFIX, ConfigError
from confpilot_es.models import Glossary
from confpilot_es.store import EsStore
from confpilot_es.telemetry import EsStoreError

logger = logging.getLogger("confpilot_es.bootstrap")


def read_glossary(path: Path) -> Glossary:
    return Glossary.model_validate(json.loads(path.read_text(encoding="utf-8")))


async def bootstrap(store: EsStore, glossary: Glossary, recreate: bool = False) -> int:
    """Idempotent: creates missing indices, then upserts every term and its percolator query."""
    created = await store.ensure_indices(recreate=recreate)
    logger.info("Indices created: %s", ", ".join(created) or "none (all present)")
    count = await store.upsert_terms(glossary.terms, version=glossary.version)
    pruned = await store.prune_seed_terms(term.id for term in glossary.terms)
    logger.info(
        "Loaded %d terms and percolator queries (glossary version %s); removed %d stale seed terms",
        count,
        glossary.version,
        pruned,
    )
    return count


async def _run(args: argparse.Namespace) -> None:
    glossary = read_glossary(args.glossary)
    store = EsStore.from_env(prefix=args.prefix)
    try:
        await bootstrap(store, glossary, recreate=args.recreate)
    finally:
        await store.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--glossary", type=Path, required=True, help="Path to a Glossary JSON file")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the indices first")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help=f"Index name prefix (default {DEFAULT_PREFIX})")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("elastic_transport").setLevel(logging.WARNING)
    try:
        asyncio.run(_run(args))
    except (ConfigError, EsStoreError, ValidationError, OSError, json.JSONDecodeError) as exc:
        logger.error("Bootstrap failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
