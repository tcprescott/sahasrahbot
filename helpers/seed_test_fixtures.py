#!/usr/bin/env python3
"""
Seed the development database with test fixtures.

Only runs when DEBUG=True. Creates a full fixture graph: tournaments, pools,
permalinks, test users, race history, and TournamentGames for the submission form.

Usage:
    poetry run python helpers/seed_test_fixtures.py           # seed (skip if data exists)
    poetry run python helpers/seed_test_fixtures.py --reset   # wipe test data then re-seed
"""

import argparse
import asyncio
import logging
import random
import sys
from datetime import datetime, timedelta, timezone

import config

if not config.DEBUG:
    print("ERROR: seed_test_fixtures.py may only run when DEBUG=True.")
    sys.exit(1)

from alttprbot import models
from tortoise import Tortoise

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Fake Discord snowflake IDs in a range that cannot collide with real ones.
FAKE_GUILD_ID = 900000000000000001
FAKE_CHANNEL_ACTIVE = 900000000000000002
FAKE_CHANNEL_INACTIVE = 900000000000000003
FAKE_REPORT_CHANNEL = 900000000000000004
ADMIN_DISCORD_ID = 900000000000000010

RACER_COUNT = 15
POOLS_PER_TOURNAMENT = 2
PERMALINKS_PER_POOL = 6
PAR_TIME_SECONDS = 5400.0  # 1:30:00

# Fake permalink hash tokens (no real seeds — just exercising the data model)
_HASHES = [
    "aAbBcCdD", "eEfFgGhH", "iIjJkKlL", "mMnNoOpP",
    "qQrRsStT", "uUvVwWxX", "yYzZ0011", "22334455",
    "66778899", "aabbccdd", "eeffgghh", "iijjkkll",
]

RACE_STATUSES = ["finished", "finished", "finished", "forfeit", "pending", "disqualified"]
REVIEW_STATUSES = ["approved", "approved", "pending", "rejected"]


def _fake_permalink_url(i: int) -> str:
    token = _HASHES[i % len(_HASHES)]
    return f"https://alttpr.com/en/h/{token}{i:04d}"


async def reset_test_data() -> None:
    logger.info("Resetting test data...")
    deleted = await models.Users.filter(test_user=True).delete()
    logger.info("  Deleted %d test users (cascades races/whitelist/permissions)", deleted)
    await models.TournamentGames.filter(episode_id__gte=90001, episode_id__lte=90003).delete()
    logger.info("  Deleted test TournamentGames")


async def seed() -> None:
    # --- Admin user ---
    admin, created = await models.Users.get_or_create(
        discord_user_id=ADMIN_DISCORD_ID,
        defaults=dict(display_name="Admin User (fixture)", test_user=True),
    )
    if created:
        logger.info("Created admin user id=%d", admin.id)
    else:
        logger.info("Admin user already exists id=%d", admin.id)

    # --- Tournaments ---
    active_t, _ = await models.AsyncTournament.get_or_create(
        channel_id=FAKE_CHANNEL_ACTIVE,
        defaults=dict(
            name="Dev Fixture Tournament (Active)",
            guild_id=FAKE_GUILD_ID,
            report_channel_id=FAKE_REPORT_CHANNEL,
            owner_id=ADMIN_DISCORD_ID,
            active=True,
            allowed_reattempts=1,
            runs_per_pool=1,
        ),
    )
    logger.info("Active tournament id=%d", active_t.id)

    inactive_t, _ = await models.AsyncTournament.get_or_create(
        channel_id=FAKE_CHANNEL_INACTIVE,
        defaults=dict(
            name="Dev Fixture Tournament (Inactive)",
            guild_id=FAKE_GUILD_ID,
            owner_id=ADMIN_DISCORD_ID,
            active=False,
            allowed_reattempts=0,
            runs_per_pool=1,
        ),
    )
    logger.info("Inactive tournament id=%d", inactive_t.id)

    # --- Admin permission ---
    await models.AsyncTournamentPermissions.get_or_create(
        tournament=active_t,
        user=admin,
        defaults=dict(role="admin"),
    )

    # --- Pools and permalinks for active tournament ---
    active_pools = []
    for pool_idx in range(POOLS_PER_TOURNAMENT):
        pool_name = f"Pool {'AB'[pool_idx]}"
        pool, _ = await models.AsyncTournamentPermalinkPool.get_or_create(
            tournament=active_t,
            name=pool_name,
            defaults=dict(preset="alttpr"),
        )
        active_pools.append(pool)
        for plink_idx in range(PERMALINKS_PER_POOL):
            url = _fake_permalink_url(pool_idx * PERMALINKS_PER_POOL + plink_idx)
            par = PAR_TIME_SECONDS if plink_idx < PERMALINKS_PER_POOL // 2 else None
            await models.AsyncTournamentPermalink.get_or_create(
                pool=pool,
                url=url,
                defaults=dict(par_time=par),
            )

    logger.info("Created %d pools with %d permalinks each for active tournament",
                len(active_pools), PERMALINKS_PER_POOL)

    # --- Racer users ---
    racers = []
    for i in range(1, RACER_COUNT + 1):
        discord_id = ADMIN_DISCORD_ID + i
        user, _ = await models.Users.get_or_create(
            discord_user_id=discord_id,
            defaults=dict(display_name=f"Racer {i} (fixture)", test_user=True),
        )
        racers.append(user)

    logger.info("Created/found %d racer users", len(racers))

    # --- Whitelist ---
    for racer in racers:
        await models.AsyncTournamentWhitelist.get_or_create(
            tournament=active_t,
            user=racer,
            defaults=dict(discord_user_id=racer.discord_user_id),
        )

    # --- Races ---
    race_count = 0
    for racer in racers:
        for pool in active_pools:
            # Fetch a permalink from this pool that hasn't been used yet by this racer
            used_plinks = await models.AsyncTournamentRace.filter(
                tournament=active_t, user=racer, permalink__pool=pool
            ).values_list("permalink_id", flat=True)
            permalinks = await models.AsyncTournamentPermalink.filter(
                pool=pool
            ).exclude(id__in=list(used_plinks)).limit(1)
            if not permalinks:
                continue
            permalink = permalinks[0]

            status = random.choice(RACE_STATUSES)
            review_status = random.choice(REVIEW_STATUSES) if status == "finished" else "pending"

            start_dt = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30),
                                                      hours=random.randint(0, 23))
            duration_s = random.randint(3600, 7200)
            end_dt = start_dt + timedelta(seconds=duration_s)

            score = round(random.uniform(0.75, 1.25), 4) if status == "finished" else None

            existing = await models.AsyncTournamentRace.filter(
                tournament=active_t, user=racer, permalink=permalink
            ).first()
            if existing:
                continue

            await models.AsyncTournamentRace.create(
                tournament=active_t,
                permalink=permalink,
                user=racer,
                thread_id=random.randint(100000000000000000, 999999999999999999),
                thread_open_time=start_dt - timedelta(minutes=5),
                status=status,
                review_status=review_status,
                start_time=start_dt if status != "pending" else None,
                end_time=end_dt if status == "finished" else None,
                score=score,
                score_updated_at=datetime.now(timezone.utc) if score is not None else None,
            )
            race_count += 1

    logger.info("Created %d races for active tournament", race_count)

    # --- TournamentGames (for submission form) ---
    for i in range(1, 4):
        episode_id = 90000 + i
        await models.TournamentGames.get_or_create(
            episode_id=episode_id,
            defaults=dict(
                event="test",
                game_number=i,
                settings={"notes": f"Test episode {i}"},
                submitted=0,
            ),
        )
    logger.info("Created TournamentGames episodes 90001–90003 for event='test'")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Fixture seeding complete!")
    print(f"  Active tournament id  : {active_t.id}")
    print(f"  Inactive tournament id: {inactive_t.id}")
    print(f"  Racers created        : {len(racers)}")
    print(f"  Races created         : {race_count}")
    print()
    print("To exercise features (dev server running):")
    print(f"  Leaderboard : /async/races/{active_t.id}/leaderboard")
    print(f"  Submit form : /submit/test  (episode 90001)")
    print(f"  Admin queue : /async/races/{active_t.id}/queue")
    print(f"  Pools page  : /async/pools/{active_t.id}")
    print("=" * 60)


async def main(reset: bool) -> None:
    from migrations import tortoise_config
    await Tortoise.init(config=tortoise_config.TORTOISE_ORM)
    try:
        if reset:
            await reset_test_data()
        await seed()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed development test fixtures.")
    parser.add_argument("--reset", action="store_true",
                        help="Delete existing test data before seeding.")
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))
