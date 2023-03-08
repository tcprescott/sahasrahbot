from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` ADD `allowed_rerolls` SMALLINT NOT NULL  DEFAULT 0;
        ALTER TABLE `asynctournamentrace` ADD `review_status` VARCHAR(8) NOT NULL  COMMENT 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected' DEFAULT 'pending';
        ALTER TABLE `asynctournamentrace` ADD `reviewer_notes` LONGTEXT;
        ALTER TABLE `asynctournamentrace` ADD `runner_notes` LONGTEXT;
        ALTER TABLE `asynctournamentrace` ADD `runner_vod_url` VARCHAR(400);
        ALTER TABLE `asynctournamentrace` ADD `reroll` BOOL NOT NULL  DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` DROP COLUMN `allowed_rerolls`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `review_status`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `reviewer_notes`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `runner_notes`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `runner_vod_url`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `reroll`;"""
