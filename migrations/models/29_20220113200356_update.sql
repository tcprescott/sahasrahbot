-- upgrade --
CREATE TABLE IF NOT EXISTS `scheduledevents` (
    `scheduled_event_id` BIGINT NOT NULL  PRIMARY KEY,
    `event_slug` VARCHAR(40) NOT NULL,
    `episode_id` INT NOT NULL
) CHARACTER SET utf8mb4;
-- downgrade --
DROP TABLE IF EXISTS `scheduledevents`;
