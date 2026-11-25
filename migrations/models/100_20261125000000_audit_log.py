from tortoise import BaseDBAsyncClient

# The audit log (`AuditLog`): one row per change someone made through SahasrahBot.
# Only adds a table. Written by hand from Tortoise's MySQL schema for the model, like
# 98 and 99.


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `audit_log` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `created_at` DATETIME(6) NOT NULL,
            `action` VARCHAR(64) NOT NULL,
            `actor_discord_id` BIGINT,
            `actor_name` VARCHAR(100),
            `via` VARCHAR(16) NOT NULL,
            `via_detail` VARCHAR(200),
            `guild_id` BIGINT,
            `target` VARCHAR(300),
            `details` JSON,
            KEY `idx_audit_log_created_7e4f1a` (`created_at`),
            KEY `idx_audit_log_action_2b9c3d` (`action`),
            KEY `idx_audit_log_actor_d_5a8e21` (`actor_discord_id`),
            KEY `idx_audit_log_guild_i_c41f07` (`guild_id`)
        ) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `audit_log`;"""
