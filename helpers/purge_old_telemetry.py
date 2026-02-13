#!/usr/bin/env python3
"""
Telemetry retention purge helper.

Removes telemetry events older than the configured retention period.
Should be run as a scheduled task (e.g., daily cron job).
"""

import asyncio
import logging
from datetime import datetime, timedelta

try:
    import config
    TELEMETRY_RETENTION_DAYS = getattr(config, 'TELEMETRY_RETENTION_DAYS', 30)
except ImportError:
    TELEMETRY_RETENTION_DAYS = 30

from alttprbot import models
from tortoise import Tortoise

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def purge_old_telemetry_events(retention_days: int = TELEMETRY_RETENTION_DAYS) -> int:
    """
    Delete telemetry events older than retention_days.
    
    Returns the number of events deleted.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    logger.info(f"Purging telemetry events older than {cutoff_date} ({retention_days} days)")
    
    # Delete old events
    deleted_count = await models.TelemetryEvent.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    logger.info(f"Purged {deleted_count} telemetry events")
    
    return deleted_count


async def get_telemetry_stats():
    """Get basic statistics about telemetry data."""
    total_count = await models.TelemetryEvent.all().count()
    
    if total_count == 0:
        logger.info("No telemetry events in database")
        return
    
    oldest = await models.TelemetryEvent.all().order_by('created_at').first()
    newest = await models.TelemetryEvent.all().order_by('-created_at').first()
    
    logger.info(f"Total events: {total_count}")
    logger.info(f"Oldest event: {oldest.created_at}")
    logger.info(f"Newest event: {newest.created_at}")
    
    # Count by surface
    surfaces = await models.TelemetryEvent.all().group_by('surface').values('surface')
    for surface_data in surfaces:
        surface = surface_data['surface']
        count = await models.TelemetryEvent.filter(surface=surface).count()
        logger.info(f"  {surface}: {count} events")


async def main():
    """Main entry point for the purge script."""
    try:
        # Initialize database connection
        from migrations import tortoise_config
        await Tortoise.init(config=tortoise_config.TORTOISE_ORM)
        
        logger.info("=" * 60)
        logger.info("Telemetry Retention Purge")
        logger.info("=" * 60)
        
        # Show stats before purge
        logger.info("\nBefore purge:")
        await get_telemetry_stats()
        
        # Run purge
        logger.info(f"\nPurging events older than {TELEMETRY_RETENTION_DAYS} days...")
        deleted_count = await purge_old_telemetry_events()
        
        # Show stats after purge
        logger.info("\nAfter purge:")
        await get_telemetry_stats()
        
        logger.info("\nPurge complete!")
        
    except Exception as e:
        logger.error(f"Purge failed: {e}", exc_info=True)
        raise
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
