from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` BIGINT;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` BIGINT;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` BIGINT;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` INT;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` INT;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` INT;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` INT;"""
