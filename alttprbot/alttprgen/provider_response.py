"""
Canonical provider response object for seed generation.

All seed providers must return this structure to ensure consistent
handling across Discord, RaceTime, and API surfaces.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ProviderMetadata:
    """Metadata about provider execution for audit and observability."""
    provider: str
    operation: str
    attempt_count: int
    latency_ms: int
    surface: Optional[str] = None  # 'discord', 'racetime', 'api'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'provider': self.provider,
            'operation': self.operation,
            'attempt_count': self.attempt_count,
            'latency_ms': self.latency_ms,
            'surface': self.surface,
        }


@dataclass
class ProviderResponse:
    """
    Canonical response structure for seed generation providers.
    
    Attributes:
        url: Direct link to the generated seed
        hash_or_id: Unique identifier for the seed (may be hash or numeric ID)
        code: File select code icons (list of item names)
        provider_meta: Execution metadata for audit and observability
        spoiler_url: Optional link to spoiler log
        version: Optional randomizer version string
    """
    url: str
    hash_or_id: str
    provider_meta: ProviderMetadata
    code: Optional[List[str]] = None
    spoiler_url: Optional[str] = None
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for serialization."""
        result = {
            'url': self.url,
            'hash_or_id': self.hash_or_id,
            'provider_meta': self.provider_meta.to_dict(),
        }
        if self.code is not None:
            result['code'] = self.code
        if self.spoiler_url is not None:
            result['spoiler_url'] = self.spoiler_url
        if self.version is not None:
            result['version'] = self.version
        return result
