from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleepisodecommentator` DROP FOREIGN KEY `fk_schedule_users_3f5a1267`;
        ALTER TABLE `scheduleepisodecommentator` DROP COLUMN `preferred_partner_id`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleepisodecommentator` ADD `preferred_partner_id` INT;
        ALTER TABLE `scheduleepisodecommentator` ADD CONSTRAINT `fk_schedule_users_3f5a1267` FOREIGN KEY (`preferred_partner_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT;"""
