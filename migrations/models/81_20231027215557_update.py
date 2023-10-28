from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `sgl2023onsitehistory` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `date` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `tournament` VARCHAR(45) NOT NULL,
    `url` VARCHAR(200) NOT NULL,
    `ip_address` VARCHAR(200) NOT NULL
) CHARACTER SET utf8mb4;;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `sgl2023onsitehistory`;"""
