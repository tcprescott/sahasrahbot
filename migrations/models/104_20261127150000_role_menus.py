from tortoise import BaseDBAsyncClient

# Role menus replace reaction roles. Adds `role_menu` and `role_menu_option` and copies
# every reaction_group / reaction_role row into them with the same ids, so existing
# menus keep working (as reaction menus) and old audit entries still point at them.
# The old tables are left untouched; a later cleanup drops them.
#
# Copying skips reaction roles with no role or whose group is gone or in another
# server. Names become titles and labels; a missing one becomes "Roles" / "Role".


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `role_menu` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `guild_id` BIGINT NOT NULL,
            `channel_id` BIGINT NOT NULL,
            `message_id` BIGINT,
            `title` VARCHAR(256) NOT NULL,
            `description` VARCHAR(4000),
            `style` VARCHAR(16) NOT NULL DEFAULT 'reactions',
            `posted_by_bot` BOOL NOT NULL DEFAULT 1,
            `single_choice` BOOL NOT NULL DEFAULT 0,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            KEY `idx_role_menu_guild_i_5c1f0e` (`guild_id`),
            KEY `idx_role_menu_message_8a2b4d` (`message_id`)
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `role_menu_option` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `role_id` BIGINT NOT NULL,
            `label` VARCHAR(80) NOT NULL,
            `description` VARCHAR(400),
            `emoji` VARCHAR(100),
            `position` INT NOT NULL DEFAULT 0,
            `menu_id` INT NOT NULL,
            CONSTRAINT `fk_role_men_role_men_3d9e71aa` FOREIGN KEY (`menu_id`) REFERENCES `role_menu` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;
        INSERT INTO `role_menu` (`id`, `guild_id`, `channel_id`, `message_id`, `title`, `description`, `style`,
                                 `posted_by_bot`, `single_choice`)
            SELECT `id`, `guild_id`, `channel_id`, `message_id`, COALESCE(NULLIF(LEFT(TRIM(`name`), 256), ''), 'Roles'),
                   NULLIF(TRIM(`description`), ''), 'reactions', COALESCE(`bot_managed`, 0) <> 0, 0
            FROM `reaction_group`;
        INSERT INTO `role_menu_option` (`id`, `menu_id`, `role_id`, `label`, `description`, `emoji`, `position`)
            SELECT r.`id`, r.`reaction_group_id`, r.`role_id`, COALESCE(NULLIF(TRIM(r.`name`), ''), 'Role'),
                   NULLIF(TRIM(r.`description`), ''), NULLIF(TRIM(r.`emoji`), ''), r.`id`
            FROM `reaction_role` r
            JOIN `reaction_group` g ON g.`id` = r.`reaction_group_id` AND g.`guild_id` = r.`guild_id`
            WHERE r.`role_id` IS NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `role_menu_option`;
        DROP TABLE IF EXISTS `role_menu`;"""
