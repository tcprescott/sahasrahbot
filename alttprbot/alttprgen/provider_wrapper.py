"""
Shared provider execution wrapper enforcing timeout, retry, and observability contract.

This module provides a single execution path for all seed providers to ensure:
- Consistent 60-second timeout per attempt
- 3-attempt exponential retry policy (1s, 2s backoff)
- Normalized exception taxonomy
- Structured logging for observability
"""

import asyncio
import logging
import time
from typing import Callable, TypeVar, Optional

import aiohttp
from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception
)

from alttprbot.alttprgen.provider_exceptions import (
    SeedProviderError,
    SeedProviderTimeoutError,
    SeedProviderUnavailableError,
    SeedProviderRateLimitError,
    SeedProviderInvalidRequestError,
    SeedProviderResponseFormatError
)
from alttprbot.alttprgen.provider_response import ProviderResponse, ProviderMetadata


logger = logging.getLogger(__name__)

T = TypeVar('T')

# Contract defaults
PROVIDER_TIMEOUT_SECONDS = 60
PROVIDER_MAX_ATTEMPTS = 3
PROVIDER_RETRY_MIN_WAIT = 1  # seconds
PROVIDER_RETRY_MAX_WAIT = 2  # seconds


def _is_retryable_error(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry."""
    # Retryable: timeouts, network errors, 5xx, 429
    if isinstance(exception, (
        asyncio.TimeoutError,
        aiohttp.ClientConnectionError,
        aiohttp.ClientConnectorError,
        SeedProviderTimeoutError,
        SeedProviderUnavailableError,
        SeedProviderRateLimitError,
    )):
        return True
    
    # Non-retryable: validation errors, 4xx (except 429), format errors
    if isinstance(exception, (
        SeedProviderInvalidRequestError,
        SeedProviderResponseFormatError,
    )):
        return False
    
    # For HTTP errors, check status code
    if isinstance(exception, aiohttp.ClientResponseError):
        if exception.status == 429:
            return True
        if 500 <= exception.status < 600:
            return True
        if 400 <= exception.status < 500:
            return False
    
    # Default: don't retry unknown exceptions
    return False


async def execute_with_contract(
    provider_func: Callable[..., T],
    provider_name: str,
    operation: str,
    *args,
    surface: Optional[str] = None,
    timeout: int = PROVIDER_TIMEOUT_SECONDS,
    max_attempts: int = PROVIDER_MAX_ATTEMPTS,
    **kwargs
) -> T:
    """
    Execute a provider function with timeout, retry, and observability contract.
    
    Args:
        provider_func: Async function to execute (must return ProviderResponse or be wrapped)
        provider_name: Name of the provider for logging/audit (e.g., 'smdash', 'avianart')
        operation: Operation type for logging/audit (e.g., 'generate_seed', 'get_presets')
        *args: Positional arguments to pass to provider_func
        surface: Calling surface ('discord', 'racetime', 'api')
        timeout: Timeout in seconds per attempt (default: 60)
        max_attempts: Maximum number of retry attempts (default: 3)
        **kwargs: Keyword arguments to pass to provider_func
    
    Returns:
        Result from provider_func (typically ProviderResponse)
    
    Raises:
        SeedProviderError: Normalized exception with provider metadata
    """
    start_time = time.time()
    attempt_number = 0
    last_exception = None
    
    try:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable_error),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=PROVIDER_RETRY_MIN_WAIT,
                max=PROVIDER_RETRY_MAX_WAIT
            ),
            reraise=True
        ):
            with attempt:
                attempt_number = attempt.retry_state.attempt_number
                
                logger.info(
                    f"Provider call: provider={provider_name}, operation={operation}, "
                    f"surface={surface}, attempt={attempt_number}/{max_attempts}"
                )
                
                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        provider_func(*args, **kwargs),
                        timeout=timeout
                    )
                    
                    # Calculate latency
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    logger.info(
                        f"Provider success: provider={provider_name}, operation={operation}, "
                        f"surface={surface}, attempt={attempt_number}, latency_ms={latency_ms}"
                    )
                    
                    # If result is already a ProviderResponse, update metadata
                    if isinstance(result, ProviderResponse):
                        result.provider_meta.attempt_count = attempt_number
                        result.provider_meta.latency_ms = latency_ms
                        if surface and not result.provider_meta.surface:
                            result.provider_meta.surface = surface
                    
                    return result
                
                except asyncio.TimeoutError as e:
                    last_exception = SeedProviderTimeoutError(
                        message=f"Provider request timed out after {timeout}s",
                        provider=provider_name,
                        operation=operation,
                        attempts=attempt_number,
                        provider_message=f"Request timed out after {timeout} seconds"
                    )
                    logger.warning(
                        f"Provider timeout: provider={provider_name}, operation={operation}, "
                        f"surface={surface}, attempt={attempt_number}, timeout={timeout}s"
                    )
                    raise last_exception
                
                except aiohttp.ClientResponseError as e:
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    # Normalize HTTP errors
                    if e.status == 429:
                        last_exception = SeedProviderRateLimitError(
                            message=f"Provider rate limit exceeded",
                            provider=provider_name,
                            operation=operation,
                            attempts=attempt_number,
                            status_code=e.status,
                            provider_message=str(e.message)
                        )
                    elif 500 <= e.status < 600:
                        last_exception = SeedProviderUnavailableError(
                            message=f"Provider returned {e.status} error",
                            provider=provider_name,
                            operation=operation,
                            attempts=attempt_number,
                            status_code=e.status,
                            provider_message=str(e.message)
                        )
                    elif 400 <= e.status < 500:
                        last_exception = SeedProviderInvalidRequestError(
                            message=f"Provider rejected request with {e.status}",
                            provider=provider_name,
                            operation=operation,
                            attempts=attempt_number,
                            status_code=e.status,
                            provider_message=str(e.message)
                        )
                    else:
                        last_exception = SeedProviderUnavailableError(
                            message=f"Provider request failed with status {e.status}",
                            provider=provider_name,
                            operation=operation,
                            attempts=attempt_number,
                            status_code=e.status,
                            provider_message=str(e.message)
                        )
                    
                    logger.warning(
                        f"Provider HTTP error: provider={provider_name}, operation={operation}, "
                        f"surface={surface}, attempt={attempt_number}, status={e.status}, "
                        f"latency_ms={latency_ms}"
                    )
                    raise last_exception
                
                except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError) as e:
                    last_exception = SeedProviderUnavailableError(
                        message=f"Provider connection failed",
                        provider=provider_name,
                        operation=operation,
                        attempts=attempt_number,
                        provider_message=str(e)
                    )
                    logger.warning(
                        f"Provider connection error: provider={provider_name}, operation={operation}, "
                        f"surface={surface}, attempt={attempt_number}, error={type(e).__name__}"
                    )
                    raise last_exception
                
                except SeedProviderError:
                    # Already normalized, just re-raise
                    raise
                
                except Exception as e:
                    # Unexpected error - wrap as format error for now
                    latency_ms = int((time.time() - start_time) * 1000)
                    last_exception = SeedProviderResponseFormatError(
                        message=f"Provider returned unexpected response: {type(e).__name__}",
                        provider=provider_name,
                        operation=operation,
                        attempts=attempt_number,
                        provider_message=str(e)
                    )
                    logger.error(
                        f"Provider unexpected error: provider={provider_name}, operation={operation}, "
                        f"surface={surface}, attempt={attempt_number}, latency_ms={latency_ms}, "
                        f"error_type={type(e).__name__}, error={str(e)}"
                    )
                    raise last_exception
    
    except RetryError:
        # All retries exhausted
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.error(
            f"Provider failure: provider={provider_name}, operation={operation}, "
            f"surface={surface}, attempts={attempt_number}, latency_ms={latency_ms}, "
            f"error_type={type(last_exception).__name__ if last_exception else 'unknown'}"
        )
        
        # Re-raise the last exception with updated attempt count
        if last_exception:
            last_exception.attempts = attempt_number
            raise last_exception
        
        # Fallback if we somehow don't have a last exception
        raise SeedProviderUnavailableError(
            message=f"Provider failed after {attempt_number} attempts",
            provider=provider_name,
            operation=operation,
            attempts=attempt_number,
            provider_message=f"Failed after {attempt_number} retry attempts"
        )
