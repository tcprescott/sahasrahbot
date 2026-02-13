from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE `telemetry_events` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `created_at` DATETIME(6) NOT NULL,
            `day_bucket` DATE NOT NULL,
            `event_name` VARCHAR(100) NOT NULL,
            `surface` VARCHAR(20) NOT NULL,
            `feature` VARCHAR(50) NOT NULL,
            `action` VARCHAR(20) NOT NULL,
            `status` VARCHAR(20) NOT NULL,
            `provider` VARCHAR(50),
            `guild_hash` VARCHAR(64),
            `duration_ms` INT,
            `error_type` VARCHAR(50),
            `sample_rate` DOUBLE NOT NULL DEFAULT 1.0,
            INDEX `idx_created_at` (`created_at`),
            INDEX `idx_day_bucket` (`day_bucket`),
            INDEX `idx_event_name` (`event_name`),
            INDEX `idx_surface` (`surface`),
            INDEX `idx_feature` (`feature`),
            INDEX `idx_status` (`status`),
            INDEX `idx_guild_hash` (`guild_hash`),
            INDEX `idx_day_surface_feature` (`day_bucket`, `surface`, `feature`),
            INDEX `idx_day_event` (`day_bucket`, `event_name`),
            INDEX `idx_day_status` (`day_bucket`, `status`)
        ) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `telemetry_events`;"""
