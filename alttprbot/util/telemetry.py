"""
Anonymous telemetry service for feature usage and reliability tracking.

Privacy-first design:
- No user IDs, usernames, or identifiable information
- Guild IDs hashed with salt (one-way, not reversible)
- Fail-open behavior: telemetry failures never impact user-facing flows
- Bounded queue: prevents unbounded memory growth
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Protocol
from collections import deque

try:
    import config
    TELEMETRY_ENABLED = getattr(config, 'TELEMETRY_ENABLED', False)
    TELEMETRY_SAMPLE_RATE = getattr(config, 'TELEMETRY_SAMPLE_RATE', 1.0)
    TELEMETRY_RETENTION_DAYS = getattr(config, 'TELEMETRY_RETENTION_DAYS', 30)
    TELEMETRY_HASH_SALT = getattr(config, 'TELEMETRY_HASH_SALT', '')
    TELEMETRY_QUEUE_SIZE = getattr(config, 'TELEMETRY_QUEUE_SIZE', 1000)
except ImportError:
    TELEMETRY_ENABLED = False
    TELEMETRY_SAMPLE_RATE = 1.0
    TELEMETRY_RETENTION_DAYS = 30
    TELEMETRY_HASH_SALT = ''
    TELEMETRY_QUEUE_SIZE = 1000

logger = logging.getLogger(__name__)


@dataclass
class TelemetryEvent:
    """
    Validated telemetry event with privacy-preserving fields.
    
    Allowed fields only - no prohibited identity data.
    """
    event_name: str  # e.g., "discord.generator.invoke"
    surface: str  # discord, racetime, api
    feature: str  # generator, daily, asynctournament, etc.
    action: str  # invoke, success, failure
    status: str  # ok, error, timeout, denied
    provider: Optional[str] = None
    guild_id: Optional[int] = None  # Will be hashed before storage
    duration_ms: Optional[int] = None
    error_type: Optional[str] = None
    sample_rate: float = 1.0
    
    # Computed fields (not in constructor)
    created_at: datetime = field(default_factory=datetime.utcnow)
    day_bucket: date = field(default_factory=lambda: datetime.utcnow().date())
    guild_hash: Optional[str] = field(default=None, init=False)
    
    def __post_init__(self):
        """Validate and hash guild_id."""
        # Hash guild_id if provided
        if self.guild_id is not None:
            self.guild_hash = hash_guild_id(self.guild_id)
        
        # Validate required fields
        if not all([self.event_name, self.surface, self.feature, self.action, self.status]):
            raise ValueError("event_name, surface, feature, action, and status are required")
        
        # Validate field lengths
        if len(self.event_name) > 100:
            raise ValueError("event_name too long (max 100 chars)")
        if len(self.surface) > 20:
            raise ValueError("surface too long (max 20 chars)")
        if len(self.feature) > 50:
            raise ValueError("feature too long (max 50 chars)")


def hash_guild_id(guild_id: int) -> str:
    """
    One-way hash of guild ID with salt.
    Not reversible - for aggregate metrics only.
    """
    if not TELEMETRY_HASH_SALT:
        # No salt configured - return a fixed hash to prevent identification
        return hashlib.sha256(b"no_salt_configured").hexdigest()
    
    value = f"{guild_id}:{TELEMETRY_HASH_SALT}"
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class TelemetryService(Protocol):
    """Interface for telemetry services."""
    
    async def record(self, event: TelemetryEvent) -> None:
        """Record a telemetry event."""
        ...
    
    async def flush(self) -> None:
        """Flush any buffered events."""
        ...


class NoOpTelemetryService:
    """
    No-op telemetry service for when telemetry is disabled.
    All operations are silent no-ops.
    """
    
    async def record(self, event: TelemetryEvent) -> None:
        """No-op: silently ignore event."""
        pass
    
    async def flush(self) -> None:
        """No-op: nothing to flush."""
        pass


class DatabaseTelemetryService:
    """
    Database-backed telemetry service with fail-open behavior.
    
    Features:
    - Bounded in-memory queue (prevents unbounded growth)
    - Async batch writes for efficiency
    - Fail-open: exceptions never propagate to caller
    - Automatic background flushing
    """
    
    def __init__(self, queue_size: int = TELEMETRY_QUEUE_SIZE):
        self.queue = deque(maxlen=queue_size)
        self._flush_lock = asyncio.Lock()
        self._dropped_count = 0
    
    async def record(self, event: TelemetryEvent) -> None:
        """
        Record event to queue. Fail-open on errors.
        
        If queue is full, oldest events are dropped.
        """
        try:
            # Check queue capacity
            if len(self.queue) >= self.queue.maxlen:
                self._dropped_count += 1
                if self._dropped_count % 100 == 0:
                    logger.warning(
                        f"Telemetry queue full, dropped {self._dropped_count} events total"
                    )
            
            self.queue.append(event)
        except Exception as e:
            # Fail-open: log but don't propagate
            logger.debug(f"Failed to queue telemetry event: {e}")
    
    async def flush(self) -> None:
        """
        Flush queued events to database.
        
        Fail-open: errors are logged but don't propagate.
        """
        if not self.queue:
            return
        
        async with self._flush_lock:
            events_to_write = list(self.queue)
            self.queue.clear()
            
            if not events_to_write:
                return
            
            try:
                from alttprbot import models
                
                # Batch insert for efficiency
                records = [
                    models.TelemetryEvent(
                        created_at=event.created_at,
                        day_bucket=event.day_bucket,
                        event_name=event.event_name,
                        surface=event.surface,
                        feature=event.feature,
                        action=event.action,
                        status=event.status,
                        provider=event.provider,
                        guild_hash=event.guild_hash,
                        duration_ms=event.duration_ms,
                        error_type=event.error_type,
                        sample_rate=event.sample_rate,
                    )
                    for event in events_to_write
                ]
                
                await models.TelemetryEvent.bulk_create(records)
                logger.debug(f"Flushed {len(records)} telemetry events")
                
            except Exception as e:
                # Fail-open: log error but don't crash
                logger.error(f"Failed to flush telemetry events: {e}", exc_info=True)


# Global telemetry service instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """
    Get the global telemetry service instance.
    
    Returns NoOpTelemetryService if telemetry is disabled,
    DatabaseTelemetryService otherwise.
    """
    global _telemetry_service
    
    if _telemetry_service is None:
        if TELEMETRY_ENABLED:
            _telemetry_service = DatabaseTelemetryService()
            logger.info("Telemetry enabled with DatabaseTelemetryService")
        else:
            _telemetry_service = NoOpTelemetryService()
            logger.info("Telemetry disabled, using NoOpTelemetryService")
    
    return _telemetry_service


async def record_event(
    event_name: str,
    surface: str,
    feature: str,
    action: str,
    status: str,
    provider: Optional[str] = None,
    guild_id: Optional[int] = None,
    duration_ms: Optional[int] = None,
    error_type: Optional[str] = None,
    sample_rate: float = TELEMETRY_SAMPLE_RATE,
) -> None:
    """
    Convenience function to record a telemetry event.
    
    This is the main entry point for instrumentation code.
    """
    try:
        event = TelemetryEvent(
            event_name=event_name,
            surface=surface,
            feature=feature,
            action=action,
            status=status,
            provider=provider,
            guild_id=guild_id,
            duration_ms=duration_ms,
            error_type=error_type,
            sample_rate=sample_rate,
        )
        
        service = get_telemetry_service()
        await service.record(event)
    except Exception as e:
        # Fail-open: never let telemetry break user flows
        logger.debug(f"Failed to record telemetry event: {e}")


async def flush_telemetry() -> None:
    """
    Flush any pending telemetry events.
    
    Should be called periodically and on shutdown.
    """
    try:
        service = get_telemetry_service()
        await service.flush()
    except Exception as e:
        logger.debug(f"Failed to flush telemetry: {e}")
