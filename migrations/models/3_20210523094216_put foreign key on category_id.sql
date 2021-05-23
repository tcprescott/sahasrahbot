-- upgrade --
ALTER TABLE `discord_server_list` MODIFY COLUMN `category_id` INT NOT NULL;
ALTER TABLE `discord_server_list` MODIFY COLUMN `category_id` INT NOT NULL;
ALTER TABLE `discord_server_list` ADD CONSTRAINT `fk_discord__discord__39f1fc92` FOREIGN KEY (`category_id`) REFERENCES `discord_server_categories` (`id`) ON DELETE CASCADE;
-- downgrade --
ALTER TABLE `discord_server_list` DROP FOREIGN KEY `fk_discord__discord__39f1fc92`;
ALTER TABLE `discord_server_list` MODIFY COLUMN `category_id` INT;
ALTER TABLE `discord_server_list` MODIFY COLUMN `category_id` INT;
