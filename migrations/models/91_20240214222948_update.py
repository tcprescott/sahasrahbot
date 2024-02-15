from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleepisodecommentator` ADD `preferred_commentary_partner_id` INT;
        ALTER TABLE `scheduleepisodecommentator` ADD CONSTRAINT `fk_schedule_schedule_ddc0d2c6` FOREIGN KEY (`preferred_commentary_partner_id`) REFERENCES `scheduleepisodecommentator` (`id`) ON DELETE RESTRICT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleepisodecommentator` DROP FOREIGN KEY `fk_schedule_schedule_ddc0d2c6`;
        ALTER TABLE `scheduleepisodecommentator` DROP COLUMN `preferred_commentary_partner_id`;"""
