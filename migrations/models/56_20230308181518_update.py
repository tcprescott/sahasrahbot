from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `racetime_id` VARCHAR(200)  UNIQUE;
        ALTER TABLE `users` ADD UNIQUE INDEX `uid_users_racetim_297b46` (`racetime_id`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP INDEX `idx_users_racetim_297b46`;
        ALTER TABLE `users` DROP COLUMN `racetime_id`;"""
