from tortoise import BaseDBAsyncClient

# The REST API's personal access tokens and the MCP server's OAuth clients, codes and
# tokens. Only adds tables. Written from Tortoise's MySQL schema generator for the
# models (like 98, by hand rather than with `aerich migrate`).


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `mcp_oauth_clients` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `client_id` VARCHAR(64) NOT NULL UNIQUE,
            `client_name` VARCHAR(255) NOT NULL,
            `redirect_uris` JSON NOT NULL,
            `grant_types` JSON NOT NULL,
            `response_types` JSON NOT NULL,
            `scope` VARCHAR(255),
            `created_at` DATETIME(6) NOT NULL
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `api_tokens` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `discord_user_id` BIGINT NOT NULL,
            `user_name` VARCHAR(100) NOT NULL,
            `name` VARCHAR(100) NOT NULL,
            `origin` VARCHAR(10) NOT NULL,
            `token_hash` VARCHAR(64) NOT NULL UNIQUE,
            `token_prefix` VARCHAR(20) NOT NULL,
            `read_only` BOOL NOT NULL,
            `refresh_token_hash` VARCHAR(64) UNIQUE,
            `refresh_expires_at` DATETIME(6),
            `created_at` DATETIME(6) NOT NULL,
            `expires_at` DATETIME(6),
            `last_used_at` DATETIME(6),
            `revoked_at` DATETIME(6),
            `oauth_client_id` INT,
            CONSTRAINT `fk_api_toke_mcp_oaut_a85c8d15` FOREIGN KEY (`oauth_client_id`) REFERENCES `mcp_oauth_clients` (`id`) ON DELETE CASCADE,
            KEY `idx_api_tokens_discord_9b3355` (`discord_user_id`)
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `mcp_authorization_codes` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `code_hash` VARCHAR(64) NOT NULL UNIQUE,
            `discord_user_id` BIGINT NOT NULL,
            `user_name` VARCHAR(100) NOT NULL,
            `redirect_uri` VARCHAR(2048) NOT NULL,
            `redirect_uri_provided_explicitly` BOOL NOT NULL,
            `code_challenge` VARCHAR(128) NOT NULL,
            `scope` VARCHAR(255),
            `resource` VARCHAR(2048),
            `read_only` BOOL NOT NULL,
            `expires_at` DATETIME(6) NOT NULL,
            `consumed_at` DATETIME(6),
            `created_at` DATETIME(6) NOT NULL,
            `client_id` INT NOT NULL,
            CONSTRAINT `fk_mcp_auth_mcp_oaut_2e5a394a` FOREIGN KEY (`client_id`) REFERENCES `mcp_oauth_clients` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `mcp_authorization_codes`;
        DROP TABLE IF EXISTS `api_tokens`;
        DROP TABLE IF EXISTS `mcp_oauth_clients`;"""
