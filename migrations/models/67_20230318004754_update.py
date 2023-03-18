from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentpermalink` ADD `par_updated_at` DATETIME(6);
        ALTER TABLE `asynctournamentpermalink` ADD `par_time` DOUBLE;
        ALTER TABLE `asynctournamentrace` ADD `score_updated_at` DATETIME(6);
        ALTER TABLE `asynctournamentrace` ADD `score` DOUBLE;
        ALTER TABLE `users` ADD `test_user` BOOL NOT NULL  DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP COLUMN `test_user`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `score_updated_at`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `score`;
        ALTER TABLE `asynctournamentpermalink` DROP COLUMN `par_updated_at`;
        ALTER TABLE `asynctournamentpermalink` DROP COLUMN `par_time`;"""
