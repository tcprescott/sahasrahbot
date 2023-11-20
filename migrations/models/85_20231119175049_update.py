from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleevent` ADD UNIQUE INDEX `uid_scheduleeve_event_s_7967a5` (`event_slug`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleevent` DROP INDEX `idx_scheduleeve_event_s_7967a5`;"""
