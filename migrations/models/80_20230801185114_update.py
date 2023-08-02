from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_election` ADD `voter_role_id` BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_election` DROP COLUMN `voter_role_id`;"""
