from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `triforcetextsconfig` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `pool_name` VARCHAR(45) NOT NULL,
    `key_name` VARCHAR(2000) NOT NULL,
    `value` VARCHAR(2000) NOT NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `triforcetextsconfig`;"""
