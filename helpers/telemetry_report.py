#!/usr/bin/env python3
"""
Telemetry usage report helper.

Generates usage reports from telemetry data for operators.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from alttprbot import models
from tortoise import Tortoise
from tortoise.functions import Count

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_daily_feature_usage(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get daily feature usage counts for the last N days.
    
    Returns aggregated counts by day, surface, feature, and action.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    results = await models.TelemetryEvent.filter(
        created_at__gte=cutoff_date
    ).group_by('day_bucket', 'surface', 'feature', 'action').annotate(
        count=Count('id')
    ).values('day_bucket', 'surface', 'feature', 'action', 'count')
    
    return results


async def get_success_failure_rates(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get success vs failure rates by feature and provider.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    results = await models.TelemetryEvent.filter(
        created_at__gte=cutoff_date,
        action='success'  # or action='failure'
    ).group_by('surface', 'feature', 'status').annotate(
        count=Count('id')
    ).values('surface', 'feature', 'status', 'count')
    
    return results


async def get_active_guild_count(days: int = 7) -> int:
    """
    Estimate active guild count (distinct guild_hash values).
    
    Note: This is an approximation due to hashing.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    guilds = await models.TelemetryEvent.filter(
        created_at__gte=cutoff_date,
        guild_hash__not_isnull=True
    ).distinct().values_list('guild_hash', flat=True)
    
    return len(guilds)


async def get_top_features(days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
    """Get the most-used features."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    results = await models.TelemetryEvent.filter(
        created_at__gte=cutoff_date
    ).group_by('surface', 'feature').annotate(
        count=Count('id')
    ).values('surface', 'feature', 'count').order_by('-count').limit(limit)
    
    return results


async def print_report(days: int = 7):
    """Generate and print a usage report."""
    logger.info("=" * 80)
    logger.info(f"Telemetry Usage Report - Last {days} Days")
    logger.info("=" * 80)
    
    # Total events
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    total_events = await models.TelemetryEvent.filter(
        created_at__gte=cutoff_date
    ).count()
    
    logger.info(f"\nTotal Events: {total_events}")
    
    if total_events == 0:
        logger.info("No telemetry data in the specified time range.")
        return
    
    # Top features
    logger.info("\nTop Features:")
    logger.info("-" * 80)
    top_features = await get_top_features(days=days)
    for i, feature in enumerate(top_features, 1):
        logger.info(
            f"{i:2d}. {feature['surface']:10s} / {feature['feature']:20s} - "
            f"{feature['count']:6d} events"
        )
    
    # Success/failure rates
    logger.info("\nSuccess/Failure Rates:")
    logger.info("-" * 80)
    rates = await get_success_failure_rates(days=days)
    
    # Group by surface/feature
    rate_map = {}
    for rate in rates:
        key = (rate['surface'], rate['feature'])
        if key not in rate_map:
            rate_map[key] = {}
        rate_map[key][rate['status']] = rate['count']
    
    for (surface, feature), statuses in sorted(rate_map.items()):
        total = sum(statuses.values())
        ok_count = statuses.get('ok', 0)
        error_count = sum(v for k, v in statuses.items() if k != 'ok')
        success_rate = (ok_count / total * 100) if total > 0 else 0
        
        logger.info(
            f"{surface:10s} / {feature:20s} - "
            f"{success_rate:5.1f}% success ({ok_count} ok, {error_count} errors)"
        )
    
    # Active guilds (if guild hashing is enabled)
    active_guilds = await get_active_guild_count(days=days)
    if active_guilds > 0:
        logger.info(f"\nApproximate Active Guilds: {active_guilds}")
    
    # Daily breakdown
    logger.info("\nDaily Feature Usage:")
    logger.info("-" * 80)
    daily_usage = await get_daily_feature_usage(days=days)
    
    # Group by day
    day_map = {}
    for usage in daily_usage:
        day = usage['day_bucket']
        if day not in day_map:
            day_map[day] = []
        day_map[day].append(usage)
    
    for day in sorted(day_map.keys(), reverse=True):
        logger.info(f"\n{day}:")
        total_day_events = sum(u['count'] for u in day_map[day])
        logger.info(f"  Total: {total_day_events} events")
        
        # Top features for the day
        top_day = sorted(day_map[day], key=lambda x: x['count'], reverse=True)[:5]
        for usage in top_day:
            logger.info(
                f"    {usage['surface']:10s} / {usage['feature']:20s} / "
                f"{usage['action']:10s} - {usage['count']:4d}"
            )


async def main():
    """Main entry point for the report script."""
    import sys
    
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid days argument: {sys.argv[1]}")
            sys.exit(1)
    
    try:
        # Initialize database connection
        from migrations import tortoise_config
        await Tortoise.init(config=tortoise_config.TORTOISE_ORM)
        
        await print_report(days=days)
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
