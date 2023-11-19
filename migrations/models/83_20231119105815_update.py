from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sgl2023onsitehistory` MODIFY COLUMN `url` VARCHAR(300) NOT NULL;
        DROP TABLE IF EXISTS `tournaments`;
        DROP TABLE IF EXISTS `sgl2020_tournament`;
        DROP TABLE IF EXISTS `sgl2020_tournament_bo3`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sgl2023onsitehistory` MODIFY COLUMN `url` VARCHAR(200) NOT NULL;"""
