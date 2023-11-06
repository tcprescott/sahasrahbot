from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sgl2023onsitehistory` MODIFY COLUMN `url` VARCHAR(300) NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sgl2023onsitehistory` MODIFY COLUMN `url` VARCHAR(200) NOT NULL;"""
