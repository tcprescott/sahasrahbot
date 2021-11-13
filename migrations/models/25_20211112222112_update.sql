-- upgrade --
CREATE TABLE IF NOT EXISTS `inquirymessageconfig` (
    `message_id` BIGINT NOT NULL  PRIMARY KEY,
    `role_id` BIGINT NOT NULL
) CHARACTER SET utf8mb4;
-- downgrade --
DROP TABLE IF EXISTS `inquirymessageconfig`;
