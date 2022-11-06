from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `audit_generated_games` MODIFY COLUMN `doors` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `audit_generated_games` MODIFY COLUMN `settings` JSON;
        ALTER TABLE `audit_generated_games` MODIFY COLUMN `timestamp` DATETIME(6)   DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `audit_messages` MODIFY COLUMN `guild_id` BIGINT;
        ALTER TABLE `audit_messages` MODIFY COLUMN `channel_id` BIGINT;
        ALTER TABLE `audit_messages` MODIFY COLUMN `message_date` DATETIME(6);
        ALTER TABLE `audit_messages` MODIFY COLUMN `user_id` BIGINT;
        ALTER TABLE `audit_messages` MODIFY COLUMN `message_id` BIGINT;
        ALTER TABLE `authorizationkeypermissions` MODIFY COLUMN `subtype` LONGTEXT;
        ALTER TABLE `config` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `discord_server_categories` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `discord_server_categories` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `inquirymessageconfig` MODIFY COLUMN `role_id` BIGINT NOT NULL;
        ALTER TABLE `multiworld` MODIFY COLUMN `owner_id` BIGINT;
        ALTER TABLE `multiworldentrant` MODIFY COLUMN `discord_user_id` BIGINT;
        ALTER TABLE `multiworldentrant` MODIFY COLUMN `multiworld_id` BIGINT NOT NULL;
        ALTER TABLE `nick_verification` MODIFY COLUMN `timestamp` DATETIME(6)   DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `nick_verification` MODIFY COLUMN `discord_user_id` BIGINT;
        ALTER TABLE `presetnamespaces` MODIFY COLUMN `discord_user_id` BIGINT NOT NULL;
        ALTER TABLE `presets` MODIFY COLUMN `content` LONGTEXT NOT NULL;
        ALTER TABLE `presets` MODIFY COLUMN `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `rtggannouncermessages` MODIFY COLUMN `message_id` BIGINT NOT NULL;
        ALTER TABLE `rtggannouncers` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `rtggannouncers` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `rtggwatcher` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `rtggwatcher` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `rtggwatcher` MODIFY COLUMN `notify_on_new_player` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `racetimekonotsegment` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `racetimekonotsegment` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `racetimekonotgame` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `racetimekonotgame` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        CREATE TABLE IF NOT EXISTS `ranked_choice_election` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `channel_id` BIGINT NOT NULL,
    `message_id` BIGINT NOT NULL,
    `owner_id` BIGINT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` VARCHAR(2000) NOT NULL,
    `show_vote_count` BOOL NOT NULL  DEFAULT 1,
    `active` BOOL NOT NULL  DEFAULT 1,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `ranked_choice_authorized_voters` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `election_id` INT NOT NULL,
    CONSTRAINT `fk_ranked_c_ranked_c_27c3c173` FOREIGN KEY (`election_id`) REFERENCES `ranked_choice_election` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `ranked_choice_candidate` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `candidate_name` VARCHAR(200) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `election_id` INT NOT NULL,
    CONSTRAINT `fk_ranked_c_ranked_c_1b1d69be` FOREIGN KEY (`election_id`) REFERENCES `ranked_choice_election` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `ranked_choice_votes` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `rank` INT,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `candidate_id` INT NOT NULL,
    `election_id` INT NOT NULL,
    CONSTRAINT `fk_ranked_c_ranked_c_0cbab0b9` FOREIGN KEY (`candidate_id`) REFERENCES `ranked_choice_candidate` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ranked_c_ranked_c_790ef614` FOREIGN KEY (`election_id`) REFERENCES `ranked_choice_election` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        ALTER TABLE `reaction_group` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `reaction_group` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `reaction_group` MODIFY COLUMN `message_id` BIGINT NOT NULL;
        ALTER TABLE `reaction_role` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `reaction_role` MODIFY COLUMN `role_id` BIGINT;
        ALTER TABLE `sgl2020_tournament` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `sgl2020_tournament` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `sgl2020_tournament_bo3` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `sgl2020_tournament_bo3` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `smz3_multiworld` MODIFY COLUMN `owner_id` BIGINT;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` VARCHAR(2000) NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` VARCHAR(2000) NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` VARCHAR(2000) NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` VARCHAR(2000) NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_channel` BIGINT NOT NULL;
        ALTER TABLE `spoiler_races` MODIFY COLUMN `started` DATETIME(6);
        ALTER TABLE `spoiler_races` MODIFY COLUMN `date` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `srl_races` MODIFY COLUMN `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `tournament_games` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `tournament_games` MODIFY COLUMN `settings` JSON;
        ALTER TABLE `tournament_games` MODIFY COLUMN `notes` LONGTEXT;
        ALTER TABLE `tournament_games` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `discord_user_id` BIGINT NOT NULL;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `tournament_results` MODIFY COLUMN `results_json` JSON;
        ALTER TABLE `tournaments` MODIFY COLUMN `coop` BOOL;
        ALTER TABLE `tournaments` MODIFY COLUMN `commentary_channel_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `guild_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `has_submission` BOOL;
        ALTER TABLE `tournaments` MODIFY COLUMN `scheduling_needs_channel_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `mod_channel_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `audit_channel_id` BIGINT;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `discord_user_id` BIGINT;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `broadcasted` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `approved` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `voice_role` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `voice_role` MODIFY COLUMN `role_id` BIGINT NOT NULL;
        ALTER TABLE `voice_role` MODIFY COLUMN `voice_channel_id` BIGINT NOT NULL;
        DROP TABLE IF EXISTS `league_playoffs`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `config` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `presets` MODIFY COLUMN `content` LONGTEXT NOT NULL;
        ALTER TABLE `presets` MODIFY COLUMN `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `srl_races` MODIFY COLUMN `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `voice_role` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `voice_role` MODIFY COLUMN `role_id` BIGINT NOT NULL;
        ALTER TABLE `voice_role` MODIFY COLUMN `voice_channel_id` BIGINT NOT NULL;
        ALTER TABLE `multiworld` MODIFY COLUMN `owner_id` BIGINT;
        ALTER TABLE `rtggwatcher` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `rtggwatcher` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `rtggwatcher` MODIFY COLUMN `notify_on_new_player` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `tournaments` MODIFY COLUMN `coop` BOOL;
        ALTER TABLE `tournaments` MODIFY COLUMN `commentary_channel_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `guild_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `has_submission` BOOL;
        ALTER TABLE `tournaments` MODIFY COLUMN `scheduling_needs_channel_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `mod_channel_id` BIGINT;
        ALTER TABLE `tournaments` MODIFY COLUMN `audit_channel_id` BIGINT;
        ALTER TABLE `reaction_role` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `reaction_role` MODIFY COLUMN `role_id` BIGINT;
        ALTER TABLE `spoiler_races` MODIFY COLUMN `started` DATETIME(6);
        ALTER TABLE `spoiler_races` MODIFY COLUMN `date` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `audit_messages` MODIFY COLUMN `guild_id` BIGINT;
        ALTER TABLE `audit_messages` MODIFY COLUMN `channel_id` BIGINT;
        ALTER TABLE `audit_messages` MODIFY COLUMN `message_date` DATETIME(6);
        ALTER TABLE `audit_messages` MODIFY COLUMN `user_id` BIGINT;
        ALTER TABLE `audit_messages` MODIFY COLUMN `message_id` BIGINT;
        ALTER TABLE `reaction_group` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `reaction_group` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `reaction_group` MODIFY COLUMN `message_id` BIGINT NOT NULL;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `discord_user_id` BIGINT;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `broadcasted` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `approved` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `triforcetexts` MODIFY COLUMN `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `rtggannouncers` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `rtggannouncers` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `smz3_multiworld` MODIFY COLUMN `owner_id` BIGINT;
        ALTER TABLE `tournament_games` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `tournament_games` MODIFY COLUMN `settings` JSON;
        ALTER TABLE `tournament_games` MODIFY COLUMN `notes` LONGTEXT;
        ALTER TABLE `tournament_games` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `nick_verification` MODIFY COLUMN `timestamp` DATETIME(6)   DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `nick_verification` MODIFY COLUMN `discord_user_id` BIGINT;
        ALTER TABLE `presetnamespaces` MODIFY COLUMN `discord_user_id` BIGINT NOT NULL;
        ALTER TABLE `multiworldentrant` MODIFY COLUMN `discord_user_id` BIGINT;
        ALTER TABLE `multiworldentrant` MODIFY COLUMN `multiworld_id` BIGINT NOT NULL;
        ALTER TABLE `racetimekonotgame` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `racetimekonotgame` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `sgl2020_tournament` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `sgl2020_tournament` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `tournament_results` MODIFY COLUMN `results_json` JSON;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` BIGINT NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` BIGINT NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` BIGINT NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_message` BIGINT NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `sgdailies` MODIFY COLUMN `announce_channel` BIGINT NOT NULL;
        ALTER TABLE `audit_generated_games` MODIFY COLUMN `doors` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `audit_generated_games` MODIFY COLUMN `settings` JSON;
        ALTER TABLE `audit_generated_games` MODIFY COLUMN `timestamp` DATETIME(6)   DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `inquirymessageconfig` MODIFY COLUMN `role_id` BIGINT NOT NULL;
        ALTER TABLE `racetimekonotsegment` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `racetimekonotsegment` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `sgl2020_tournament_bo3` MODIFY COLUMN `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `sgl2020_tournament_bo3` MODIFY COLUMN `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `rtggannouncermessages` MODIFY COLUMN `message_id` BIGINT NOT NULL;
        ALTER TABLE `discord_server_categories` MODIFY COLUMN `guild_id` BIGINT NOT NULL;
        ALTER TABLE `discord_server_categories` MODIFY COLUMN `channel_id` BIGINT NOT NULL;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `discord_user_id` BIGINT NOT NULL;
        ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `authorizationkeypermissions` MODIFY COLUMN `subtype` LONGTEXT;
        DROP TABLE IF EXISTS `ranked_choice_authorized_voters`;
        DROP TABLE IF EXISTS `ranked_choice_candidate`;
        DROP TABLE IF EXISTS `ranked_choice_election`;
        DROP TABLE IF EXISTS `ranked_choice_votes`;"""
