from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `rtggoverridewhitelist` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `racetime_id` VARCHAR(50) NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `reason` VARCHAR(200),
    `expires` DATETIME(6)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `rtggoverridewhitelist`;"""
