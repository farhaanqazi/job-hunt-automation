from pathlib import Path

import yaml

from jobhunt.sources.base import SourceMetadata


def load_source_catalog(path: str = "config/source_catalog.yaml") -> dict[str, SourceMetadata]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {
        source_id: SourceMetadata(source_id=source_id, **source)
        for source_id, source in data["sources"].items()
    }
