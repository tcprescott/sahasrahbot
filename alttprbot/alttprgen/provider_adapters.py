"""
Adapter for SM Dash randomizer provider to use the reliability contract.

This adapter wraps the legacy smdash helper functions to enforce
timeout, retry, and normalized error handling through the shared contract.
"""

import logging
from typing import Optional

from alttprbot.alttprgen.provider_wrapper import execute_with_contract
from alttprbot.alttprgen.provider_response import ProviderResponse, ProviderMetadata
from alttprbot.alttprgen.provider_exceptions import SeedProviderResponseFormatError
from alttprbot.alttprgen.randomizer import smdash as smdash_legacy


logger = logging.getLogger(__name__)


class SMDashProvider:
    """
    Contract-compliant adapter for SM Dash randomizer.
    
    Wraps the legacy smdash.create_smdash() function to enforce
    the shared provider reliability contract.
    """
    
    PROVIDER_NAME = "smdash"
    
    @classmethod
    async def generate_seed(
        cls,
        mode: str = "classic_mm",
        spoiler: bool = False,
        surface: Optional[str] = None
    ) -> ProviderResponse:
        """
        Generate a SM Dash seed with contract enforcement.
        
        Args:
            mode: Dash preset mode (default: 'classic_mm')
            spoiler: Whether to include spoiler log (default: False)
            surface: Calling surface for audit ('discord', 'racetime', 'api')
        
        Returns:
            ProviderResponse with seed URL and metadata
        
        Raises:
            SeedProviderError: Normalized exception with provider metadata
        """
        async def _generate():
            # Call legacy smdash function
            url = await smdash_legacy.create_smdash(mode=mode, spoiler=spoiler)
            
            # Validate response
            if not url or not isinstance(url, str):
                raise SeedProviderResponseFormatError(
                    message="smdash returned invalid URL",
                    provider=cls.PROVIDER_NAME,
                    operation="generate_seed",
                    attempts=1,
                    provider_message=f"Expected URL string, got: {type(url).__name__}"
                )
            
            # Construct canonical response
            # Note: smdash returns a URL but no hash/ID in the response
            # We extract it from the URL if possible
            hash_or_id = url.split('/')[-1] if '/' in url else url
            
            return ProviderResponse(
                url=url,
                hash_or_id=hash_or_id,
                provider_meta=ProviderMetadata(
                    provider=cls.PROVIDER_NAME,
                    operation="generate_seed",
                    attempt_count=1,  # Will be updated by wrapper
                    latency_ms=0,     # Will be updated by wrapper
                    surface=surface
                ),
                code=None,  # smdash doesn't provide file select codes
                spoiler_url=url if spoiler else None,
                version=None  # smdash doesn't expose version in response
            )
        
        # Execute through contract wrapper
        return await execute_with_contract(
            _generate,
            provider_name=cls.PROVIDER_NAME,
            operation="generate_seed",
            surface=surface
        )
    
    @classmethod
    async def get_presets(cls, surface: Optional[str] = None) -> list:
        """
        Get available Dash presets with contract enforcement.
        
        Args:
            surface: Calling surface for audit ('discord', 'racetime', 'api')
        
        Returns:
            List of preset names
        
        Raises:
            SeedProviderError: Normalized exception with provider metadata
        """
        async def _get_presets():
            return await smdash_legacy.get_smdash_presets()
        
        # Execute through contract wrapper
        return await execute_with_contract(
            _get_presets,
            provider_name=cls.PROVIDER_NAME,
            operation="get_presets",
            surface=surface
        )


# Backward compatibility: provide wrapper functions that match legacy API
async def create_smdash(mode: str = "classic_mm", spoiler: bool = False) -> str:
    """
    Legacy-compatible wrapper for smdash generation.
    
    This function provides backward compatibility with existing code
    that calls smdash.create_smdash() directly.
    
    Note: This bypasses the contract wrapper for now to preserve
    exact legacy behavior. Migration to use SMDashProvider directly
    should happen in Phase 2.
    """
    return await smdash_legacy.create_smdash(mode=mode, spoiler=spoiler)


async def get_smdash_presets() -> list:
    """
    Legacy-compatible wrapper for getting smdash presets.
    
    This function provides backward compatibility with existing code
    that calls smdash.get_smdash_presets() directly.
    
    Note: This bypasses the contract wrapper for now to preserve
    exact legacy behavior. Migration to use SMDashProvider directly
    should happen in Phase 2.
    """
    return await smdash_legacy.get_smdash_presets()
