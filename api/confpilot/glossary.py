"""Load the glossary: GLOSSARY_PATH, then content/glossary.json, then the contracts sample."""

import logging
from pathlib import Path

from pydantic import ValidationError

from confpilot.models import Glossary

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_GLOSSARY = REPO_ROOT / "content" / "glossary.json"
SAMPLE_GLOSSARY = REPO_ROOT / "contracts" / "fixtures" / "glossary.sample.json"

_log = logging.getLogger(__name__)


def load_glossary(glossary_path: Path | None = None) -> Glossary:
    """Return the first candidate that exists and is valid. Raise if none is."""
    candidates = [p for p in (glossary_path, CONTENT_GLOSSARY, SAMPLE_GLOSSARY) if p is not None]
    for path in candidates:
        if not path.is_file():
            if path == glossary_path:
                _log.warning("GLOSSARY_PATH does not exist, falling back: %s", path)
            continue
        try:
            glossary = Glossary.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            _log.error("glossary at %s is unusable, falling back: %s", path, exc)
            continue
        _log.info(
            "loaded glossary %s (%d terms) from %s", glossary.version, len(glossary.terms), path
        )
        return glossary
    raise RuntimeError(f"No usable glossary found. Tried: {', '.join(map(str, candidates))}")
