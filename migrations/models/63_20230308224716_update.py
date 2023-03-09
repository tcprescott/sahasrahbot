from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `review_status` VARCHAR(20) NOT NULL  DEFAULT 'pending';
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `review_status` VARCHAR(20) NOT NULL  DEFAULT 'pending';
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `review_status` VARCHAR(20) NOT NULL  DEFAULT 'pending';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `review_status` VARCHAR(8) NOT NULL  COMMENT 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected' DEFAULT 'pending';
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `review_status` VARCHAR(8) NOT NULL  COMMENT 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected' DEFAULT 'pending';
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `review_status` VARCHAR(8) NOT NULL  COMMENT 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected' DEFAULT 'pending';"""
