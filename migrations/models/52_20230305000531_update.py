from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `srlnick` ADD `display_name` VARCHAR(200);
        ALTER TABLE `srlnick` ADD INDEX `idx_srlnick_display_b50acb` (`display_name`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `srlnick` DROP INDEX `idx_srlnick_display_b50acb`;
        ALTER TABLE `srlnick` DROP COLUMN `display_name`;"""
