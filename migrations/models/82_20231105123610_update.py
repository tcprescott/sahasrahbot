from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `triforcetexts` ALTER COLUMN `approved` DROP DEFAULT;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `approved` BOOL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `triforcetexts` MODIFY COLUMN `approved` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `triforcetexts` ALTER COLUMN `approved` SET DEFAULT 0;"""
