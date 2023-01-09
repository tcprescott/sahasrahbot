from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `guild_id` BIGINT;
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `channel_id` BIGINT;
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `description` VARCHAR(2000);
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `message_id` BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `description` VARCHAR(2000) NOT NULL;
        ALTER TABLE `ranked_choice_election` MODIFY COLUMN `message_id` BIGINT NOT NULL;"""
