-- upgrade --
CREATE TABLE IF NOT EXISTS `audit_generated_games` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `randomizer` VARCHAR(45) NOT NULL,
    `hash_id` VARCHAR(50) NOT NULL,
    `permalink` VARCHAR(2000) NOT NULL,
    `settings` JSON NOT NULL,
    `gentype` VARCHAR(45) NOT NULL,
    `genoption` VARCHAR(45) NOT NULL,
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `customizer` INT NOT NULL,
    KEY `idx_audit_gener_hash_id_4114aa` (`hash_id`),
    KEY `idx_audit_gener_gentype_80191a` (`gentype`),
    KEY `idx_audit_gener_genopti_d4e2e3` (`genoption`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `audit_messages` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `message_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `message_date` DATETIME(6) NOT NULL,
    `content` VARCHAR(4000) NOT NULL,
    `attachment` VARCHAR(2000) NOT NULL,
    `deleted` INT NOT NULL  DEFAULT 0
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `config` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `parameter` VARCHAR(45) NOT NULL,
    `value` VARCHAR(45) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `daily` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hash` VARCHAR(45) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `discord_server_categories` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `order` INT NOT NULL  DEFAULT 0,
    `guild_id` BIGINT NOT NULL,
    `channel_id` BIGINT NOT NULL,
    `category_title` VARCHAR(200) NOT NULL,
    `category_description` VARCHAR(200) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `discord_server_list` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `server_description` VARCHAR(200) NOT NULL,
    `invite_id` VARCHAR(45) NOT NULL,
    `category_id` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `league_playoffs` (
    `episode_id` INT NOT NULL  PRIMARY KEY,
    `playoff_round` VARCHAR(45) NOT NULL,
    `game_number` INT NOT NULL,
    `type` VARCHAR(45) NOT NULL,
    `preset` VARCHAR(45) NOT NULL,
    `settings` JSON NOT NULL,
    `submitted` SMALLINT NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `mention_counters` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `role_id` BIGINT NOT NULL UNIQUE,
    `counter` INT NOT NULL  DEFAULT 1,
    `last_used` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `nick_verification` (
    `key` BIGINT NOT NULL  PRIMARY KEY,
    `discord_user_id` BIGINT NOT NULL,
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `patch_distribution` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `patch_id` VARCHAR(45) NOT NULL,
    `game` VARCHAR(45) NOT NULL,
    `used` SMALLINT NOT NULL,
    KEY `idx_patch_distr_used_7a58f6` (`used`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `reaction_group` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `channel_id` BIGINT NOT NULL,
    `message_id` BIGINT NOT NULL,
    `name` VARCHAR(400) NOT NULL,
    `description` VARCHAR(1000) NOT NULL,
    `bot_managed` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `reaction_role` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `reaction_group_id` BIGINT NOT NULL,
    `role_id` BIGINT NOT NULL,
    `name` VARCHAR(45) NOT NULL,
    `emoji` VARCHAR(200) NOT NULL,
    `protect_mentions` SMALLINT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sgl2020_tournament` (
    `episode_id` INT NOT NULL  PRIMARY KEY,
    `room_name` VARCHAR(100) NOT NULL,
    `event` VARCHAR(45) NOT NULL,
    `platform` VARCHAR(45) NOT NULL,
    `permalink` VARCHAR(200) NOT NULL,
    `seed` VARCHAR(200) NOT NULL,
    `password` VARCHAR(200) NOT NULL,
    `status` VARCHAR(45) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sgl2020_tournament_bo3` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `episode_id` INT NOT NULL,
    `room_name` VARCHAR(100) NOT NULL,
    `event` VARCHAR(45) NOT NULL,
    `platform` VARCHAR(45) NOT NULL,
    `permalink` VARCHAR(200) NOT NULL,
    `seed` VARCHAR(200) NOT NULL,
    `password` VARCHAR(200) NOT NULL,
    `status` VARCHAR(45) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `smz3_multiworld` (
    `message_id` BIGINT NOT NULL  PRIMARY KEY,
    `owner_id` BIGINT NOT NULL,
    `randomizer` VARCHAR(45) NOT NULL,
    `preset` VARCHAR(45) NOT NULL,
    `status` VARCHAR(20) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `srlnick` (
    `discord_user_id` BIGINT NOT NULL  PRIMARY KEY,
    `srl_nick` VARCHAR(200) NOT NULL,
    `twitch_name` VARCHAR(200) NOT NULL,
    `rtgg_id` VARCHAR(200) NOT NULL,
    `srl_verified` SMALLINT NOT NULL,
    KEY `idx_srlnick_srl_nic_07963e` (`srl_nick`),
    KEY `idx_srlnick_twitch__ac21e3` (`twitch_name`),
    KEY `idx_srlnick_rtgg_id_f7ec99` (`rtgg_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sgdailies` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `slug` VARCHAR(45) NOT NULL,
    `guild_id` BIGINT NOT NULL,
    `announce_channel` BIGINT NOT NULL,
    `announce_message` BIGINT NOT NULL,
    `racetime_category` VARCHAR(45) NOT NULL,
    `racetime_goal` VARCHAR(45) NOT NULL,
    `race_info` VARCHAR(2000) NOT NULL,
    `active` SMALLINT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `spoiler_races` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `srl_id` VARCHAR(45) NOT NULL,
    `spoiler_url` VARCHAR(255) NOT NULL,
    `studytime` INT NOT NULL,
    `date` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `started` DATETIME(6) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `srl_races` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `srl_id` VARCHAR(45) NOT NULL,
    `goal` VARCHAR(200) NOT NULL,
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `message` VARCHAR(200) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `tournament_games` (
    `episode_id` INT NOT NULL  PRIMARY KEY,
    `event` VARCHAR(45) NOT NULL,
    `game_number` INT NOT NULL,
    `settings` JSON NOT NULL,
    `submitted` SMALLINT NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `tournament_results` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `srl_id` VARCHAR(45) NOT NULL,
    `episode_id` VARCHAR(45) NOT NULL,
    `permalink` VARCHAR(200) NOT NULL,
    `spoiler` VARCHAR(200) NOT NULL,
    `event` VARCHAR(45) NOT NULL,
    `status` VARCHAR(45) NOT NULL,
    `results_json` JSON NOT NULL,
    `week` VARCHAR(45) NOT NULL,
    `written_to_gsheet` SMALLINT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `tournaments` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `schedule_type` VARCHAR(45) NOT NULL,
    `slug` VARCHAR(45) NOT NULL,
    `guild_id` BIGINT NOT NULL,
    `helper_roles` VARCHAR(4000) NOT NULL,
    `audit_channel_id` BIGINT NOT NULL,
    `commentary_channel_id` BIGINT NOT NULL,
    `scheduling_needs_channel_id` BIGINT NOT NULL,
    `scheduling_needs_tracker` SMALLINT NOT NULL,
    `mod_channel_id` BIGINT NOT NULL,
    `tracker_roles` VARCHAR(4000) NOT NULL,
    `commentator_roles` VARCHAR(4000) NOT NULL,
    `mod_roles` VARCHAR(4000) NOT NULL,
    `admin_roles` VARCHAR(4000) NOT NULL,
    `category` VARCHAR(200) NOT NULL,
    `goal` VARCHAR(200) NOT NULL,
    `active` SMALLINT NOT NULL,
    `lang` VARCHAR(20) NOT NULL,
    UNIQUE KEY `uid_tournaments_schedul_687efa` (`schedule_type`, `slug`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `twitch_channels` (
    `channel` VARCHAR(200) NOT NULL  PRIMARY KEY,
    `status` VARCHAR(45) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `twitch_command_text` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `channel` VARCHAR(200) NOT NULL,
    `command` VARCHAR(45) NOT NULL,
    `content` VARCHAR(4000) NOT NULL,
    UNIQUE KEY `uid_twitch_comm_channel_16ae77` (`channel`, `command`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `voicerole` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `voice_channel_id` BIGINT NOT NULL,
    `role_id` BIGINT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(20) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
