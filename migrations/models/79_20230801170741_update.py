from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `racerverification` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `message_id` BIGINT,
    `guild_id` BIGINT NOT NULL,
    `role_id` BIGINT NOT NULL,
    `racetime_categories` VARCHAR(2000),
    `use_alttpr_ladder` BOOL NOT NULL  DEFAULT 0,
    `minimum_races` INT NOT NULL,
    `time_period_days` INT NOT NULL  DEFAULT 365,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `racerverification`;"""
