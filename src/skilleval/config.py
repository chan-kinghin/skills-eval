"""Configuration loading and validation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import yaml

from skilleval.models import ModelEntry, TaskConfig, TaskFolder

logger = logging.getLogger(__name__)


def load_task(task_path: str | Path) -> TaskFolder:
    """Load and validate a complete task folder."""
    task_path = Path(task_path).resolve()
    logger.debug("Loading task from %s", task_path)

    config_path = task_path / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"No config.yaml found in {task_path}")

    raw = yaml.safe_load(config_path.read_text())
    config = TaskConfig(**(raw or {}))

    input_dir = task_path / "input"
    expected_dir = task_path / "expected"

    input_files = sorted(p for p in input_dir.iterdir() if p.is_file() and not p.name.startswith("."))
    expected_files = sorted(
        p for p in expected_dir.iterdir() if p.is_file() and not p.name.startswith(".")
    )

    if not input_dir.exists() or not input_files:
        raise ValueError(f"input/ directory missing or empty in {task_path}")
    if not expected_dir.exists() or not expected_files:
        raise ValueError(f"expected/ directory missing or empty in {task_path}")

    skill = _read_optional(task_path / "skill.md")
    prompt = _read_optional(task_path / "prompt.md")
    meta_skills = _load_meta_skills(task_path)

    return TaskFolder(
        path=task_path,
        input_files=input_files,
        expected_files=expected_files,
        config=config,
        skill=skill,
        prompt=prompt,
        meta_skills=meta_skills,
    )


def _read_optional(path: Path) -> str | None:
    """Read a file if it exists, return None otherwise."""
    if path.exists():
        return path.read_text().strip()
    return None


def _load_meta_skills(task_path: Path) -> dict[str, str]:
    """Load all meta-skill-*.md files from the task folder."""
    meta_skills = {}
    for f in sorted(task_path.glob("meta-skill-*.md")):
        name = f.stem.replace("meta-skill-", "")
        content = f.read_text().strip()
        if content:
            meta_skills[name] = content
    return meta_skills


def load_catalog(catalog_path: str | Path | None = None) -> list[ModelEntry]:
    """Load model catalog with fallback chain."""
    text = _load_catalog_text(catalog_path)
    raw = yaml.safe_load(text)
    if not isinstance(raw, list):
        raise ValueError(f"Model catalog must be a YAML list, got {type(raw).__name__}")
    return [ModelEntry(**entry) for entry in raw]


def _load_catalog_text(catalog_path: str | Path | None) -> str:
    """Load model catalog content with fallback chain.

    Resolution order:
    1. Explicit path from --catalog flag
    2. ./models.yaml in current directory
    3. ~/.config/skilleval/models.yaml (user-global)
    4. Bundled default shipped with the package
    """
    candidates: list[Path] = []

    if catalog_path:
        candidates.append(Path(catalog_path))

    candidates.extend([
        Path.cwd() / "models.yaml",
        Path.home() / ".config" / "skilleval" / "models.yaml",
    ])

    for path in candidates:
        if path.exists():
            logger.debug("Loading catalog from %s", path)
            return path.read_text()

    # Fall back to bundled default — read via Traversable to avoid
    # context-manager lifecycle issues with importlib.resources.as_file.
    import importlib.resources

    ref = importlib.resources.files("skilleval") / "default_models.yaml"
    try:
        text = ref.read_text(encoding="utf-8")
        logger.debug("Loading catalog from bundled default_models.yaml")
        return text
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        "No model catalog found. Create a models.yaml or use --catalog to specify one."
    )


def filter_available(models: list[ModelEntry]) -> list[ModelEntry]:
    """Return only models available for use.

    A model is considered available if either:
    - its environment variable specified by `env_key` is set, or
    - it is an ad-hoc model instance carrying a non-empty `api_key`.
    """
    available: list[ModelEntry] = []
    for m in models:
        if os.environ.get(m.env_key):
            available.append(m)
            continue
        # Allow ad-hoc models that embed the API key directly
        if m.api_key and m.api_key.strip():
            available.append(m)
    logger.debug("%d of %d models available after filtering", len(available), len(models))
    return available


def filter_by_names(models: list[ModelEntry], names: list[str]) -> list[ModelEntry]:
    """Filter models by name list. Raises if any name is not found."""
    name_set = set(names)
    found = [m for m in models if m.name in name_set]
    missing = name_set - {m.name for m in found}
    if missing:
        raise ValueError(f"Models not found in catalog: {', '.join(sorted(missing))}")
    return found


def build_adhoc_model(
    endpoint: str,
    api_key: str,
    model_name: str,
    input_cost: float = 0.0,
    output_cost: float = 0.0,
) -> ModelEntry:
    """Construct and validate an ad-hoc ModelEntry.

    Validation:
    - `endpoint` must be a valid http(s) URL
    - `model_name` must be non-empty
    - costs default to $0 when not provided
    """
    # Validate endpoint URL
    parsed = urlparse(endpoint or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Invalid endpoint URL; must be http(s)://host[:port]/...")

    # Validate model name
    if not (model_name or "").strip():
        raise ValueError("Model name must be provided and non-empty")

    return ModelEntry.adhoc(
        endpoint=endpoint,
        api_key=api_key,
        model_name=model_name,
        input_cost=input_cost,
        output_cost=output_cost,
    )
