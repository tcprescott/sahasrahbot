from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` DROP FOREIGN KEY `fk_asynctou_asynctou_3705b7e2`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `pool_id`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ADD `pool_id` INT NOT NULL;
        ALTER TABLE `asynctournamentrace` ADD CONSTRAINT `fk_asynctou_asynctou_3705b7e2` FOREIGN KEY (`pool_id`) REFERENCES `asynctournamentpermalinkpool` (`id`) ON DELETE CASCADE;"""
