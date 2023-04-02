from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentpermissions` ADD `discord_role_id` BIGINT;
        ALTER TABLE `asynctournamentpermissions` MODIFY COLUMN `user_id` INT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentpermissions` DROP COLUMN `discord_role_id`;
        ALTER TABLE `asynctournamentpermissions` MODIFY COLUMN `user_id` INT NOT NULL;"""
