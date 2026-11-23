from tortoise import BaseDBAsyncClient

# DESTRUCTIVE: drops every async tournament table and all of its data.
# The async tournament feature was removed from the bot and web app.
# Take a backup of these tables before running `aerich upgrade` if the data
# might ever be wanted again. The downgrade recreates empty tables only.


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `asynctournamentreviewnotes`;
        DROP TABLE IF EXISTS `asynctournamentrace`;
        DROP TABLE IF EXISTS `asynctournamentwhitelist`;
        DROP TABLE IF EXISTS `asynctournamentpermissions`;
        DROP TABLE IF EXISTS `asynctournamentauditlog`;
        DROP TABLE IF EXISTS `asynctournamentliverace`;
        DROP TABLE IF EXISTS `asynctournamentpermalink`;
        DROP TABLE IF EXISTS `asynctournamentpermalinkpool`;
        DROP TABLE IF EXISTS `asynctournament`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `asynctournament` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `name` VARCHAR(45) NOT NULL,
            `guild_id` BIGINT NOT NULL,
            `channel_id` BIGINT NOT NULL UNIQUE,
            `report_channel_id` BIGINT,
            `owner_id` BIGINT NOT NULL,
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `active` BOOL NOT NULL  DEFAULT 1,
            `allowed_reattempts` SMALLINT NOT NULL  DEFAULT 0,
            `runs_per_pool` SMALLINT NOT NULL  DEFAULT 1,
            `customization` VARCHAR(45) NOT NULL  DEFAULT 'default'
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentpermalinkpool` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `name` VARCHAR(45) NOT NULL,
            `preset` VARCHAR(45),
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `tournament_id` INT NOT NULL,
            UNIQUE KEY `uid_asynctourna_tournam_f7028a` (`tournament_id`, `name`),
            CONSTRAINT `fk_asynctou_asynctou_fcfa7dda` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentpermalink` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `url` VARCHAR(200) NOT NULL,
            `notes` VARCHAR(200),
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `live_race` BOOL NOT NULL  DEFAULT 0,
            `par_time` DOUBLE,
            `par_updated_at` DATETIME(6),
            `pool_id` INT NOT NULL,
            CONSTRAINT `fk_asynctou_asynctou_5535a48e` FOREIGN KEY (`pool_id`) REFERENCES `asynctournamentpermalinkpool` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentliverace` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `racetime_slug` VARCHAR(200)  UNIQUE,
            `episode_id` INT  UNIQUE,
            `match_title` VARCHAR(200),
            `status` VARCHAR(45) NOT NULL  DEFAULT 'scheduled',
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `permalink_id` INT,
            `pool_id` INT NOT NULL,
            `tournament_id` INT NOT NULL,
            CONSTRAINT `fk_asynctou_asynctou_b38c783e` FOREIGN KEY (`permalink_id`) REFERENCES `asynctournamentpermalink` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_asynctou_331f22e7` FOREIGN KEY (`pool_id`) REFERENCES `asynctournamentpermalinkpool` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_asynctou_7eb2f298` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentauditlog` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `action` VARCHAR(45) NOT NULL,
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `details` LONGTEXT,
            `tournament_id` INT NOT NULL,
            `user_id` INT,
            CONSTRAINT `fk_asynctou_asynctou_07157358` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_users_832328f7` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentpermissions` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `discord_role_id` BIGINT,
            `role` VARCHAR(45) NOT NULL,
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `tournament_id` INT NOT NULL,
            `user_id` INT,
            CONSTRAINT `fk_asynctou_asynctou_b1833ce5` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_users_4d24175e` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentrace` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `thread_id` BIGINT,
            `thread_open_time` DATETIME(6),
            `thread_timeout_time` DATETIME(6),
            `start_time` DATETIME(6),
            `end_time` DATETIME(6),
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `status` VARCHAR(45) NOT NULL  DEFAULT 'pending',
            `reattempted` BOOL NOT NULL  DEFAULT 0,
            `reattempt_reason` LONGTEXT,
            `runner_notes` LONGTEXT,
            `runner_vod_url` VARCHAR(400),
            `run_collection_rate` VARCHAR(100),
            `run_igt` VARCHAR(100),
            `review_status` VARCHAR(20) NOT NULL  DEFAULT 'pending',
            `reviewed_at` DATETIME(6),
            `reviewer_notes` LONGTEXT,
            `score` DOUBLE,
            `score_updated_at` DATETIME(6),
            `live_race_id` INT,
            `permalink_id` INT NOT NULL,
            `reviewed_by_id` INT,
            `tournament_id` INT NOT NULL,
            `user_id` INT NOT NULL,
            CONSTRAINT `fk_asynctou_asynctou_d1ab3397` FOREIGN KEY (`live_race_id`) REFERENCES `asynctournamentliverace` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_asynctou_10537e98` FOREIGN KEY (`permalink_id`) REFERENCES `asynctournamentpermalink` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_users_2566e29f` FOREIGN KEY (`reviewed_by_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_asynctou_652b97e9` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_users_306c561f` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentreviewnotes` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `note` LONGTEXT NOT NULL,
            `author_id` INT NOT NULL,
            `race_id` INT NOT NULL,
            CONSTRAINT `fk_asynctou_users_4f203cf2` FOREIGN KEY (`author_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
            CONSTRAINT `fk_asynctou_asynctou_98fa4948` FOREIGN KEY (`race_id`) REFERENCES `asynctournamentrace` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentwhitelist` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `discord_user_id` BIGINT,
            `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
            `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `tournament_id` INT NOT NULL,
            `user_id` INT NOT NULL,
            CONSTRAINT `fk_asynctou_asynctou_dbcd135c` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_asynctou_users_7774d4d6` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
        ) CHARACTER SET utf8mb4;"""
