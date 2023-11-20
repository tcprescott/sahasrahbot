from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `scheduleevent` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `event_slug` VARCHAR(50) NOT NULL,
    `description` LONGTEXT NOT NULL,
    `stream_delay` INT NOT NULL  DEFAULT 0,
    `open_player_signup` BOOL NOT NULL  DEFAULT 1,
    `open_restreamer_signup` BOOL NOT NULL  DEFAULT 1,
    `open_commentator_signup` BOOL NOT NULL  DEFAULT 1,
    `open_tracker_signup` BOOL NOT NULL  DEFAULT 1,
    `max_players` INT NOT NULL  DEFAULT 2,
    `max_commentators` INT NOT NULL  DEFAULT 2,
    `max_trackers` INT NOT NULL  DEFAULT 1,
    `max_restreamers` INT NOT NULL  DEFAULT 1
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `scheduleepisode` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `episode_number` INT NOT NULL,
    `scheduled_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `when_countdown` DATETIME(6) NOT NULL,
    `runner_notes` LONGTEXT,
    `private_notes` LONGTEXT,
    `event_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_4297675f` FOREIGN KEY (`event_id`) REFERENCES `scheduleevent` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `scheduleepisodecommentator` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `approved` BOOL NOT NULL  DEFAULT 0,
    `submitted_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `submitter_notes` LONGTEXT,
    `episode_id` INT NOT NULL,
    `preferred_partner_id` INT,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_335fd700` FOREIGN KEY (`episode_id`) REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_users_3f5a1267` FOREIGN KEY (`preferred_partner_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_schedule_users_0e3289dd` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `scheduleepisodeplayer` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `episode_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_ea65c076` FOREIGN KEY (`episode_id`) REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_users_feb1c535` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `scheduleepisoderestreamer` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `approved` BOOL NOT NULL  DEFAULT 0,
    `submitted_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `submitter_notes` LONGTEXT,
    `episode_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_7258deba` FOREIGN KEY (`episode_id`) REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_users_f20d9ca9` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `scheduleepisodetracker` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `approved` BOOL NOT NULL  DEFAULT 0,
    `submitted_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `submitter_notes` LONGTEXT,
    `episode_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_14ec2b66` FOREIGN KEY (`episode_id`) REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_users_82959a52` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `schedulerole` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `event_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_b9016a5b` FOREIGN KEY (`event_id`) REFERENCES `scheduleevent` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `schedulerolemember` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `role_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_14b0cb3e` FOREIGN KEY (`role_id`) REFERENCES `schedulerole` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_users_b183447c` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `scheduleepisode`;
        DROP TABLE IF EXISTS `scheduleepisodecommentator`;
        DROP TABLE IF EXISTS `scheduleepisodeplayer`;
        DROP TABLE IF EXISTS `scheduleepisoderestreamer`;
        DROP TABLE IF EXISTS `scheduleepisodetracker`;
        DROP TABLE IF EXISTS `scheduleevent`;
        DROP TABLE IF EXISTS `schedulerole`;
        DROP TABLE IF EXISTS `schedulerolemember`;"""
