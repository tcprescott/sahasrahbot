-- upgrade --
ALTER TABLE `scheduledevents` ADD UNIQUE INDEX `uid_scheduledev_episode_bd34d2` (`episode_id`);
-- downgrade --
ALTER TABLE `scheduledevents` DROP INDEX `idx_scheduledev_episode_bd34d2`;
