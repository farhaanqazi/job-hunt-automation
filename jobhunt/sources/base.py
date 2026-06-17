from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class SourceMetadata(BaseModel):
    source_id: str
    display_name: str
    enabled: bool
    source_type: str
    data_access: str
    source_code_license: str
    data_rights: str
    redistribution_allowed: bool
    requires_attribution: bool
    canonical_url_required: bool
    rate_limit_per_minute: int
    usage_notes: str


class JobSource(ABC):
    source_id: str

    @abstractmethod
    def fetch(self) -> list[Any]:
        raise NotImplementedError
