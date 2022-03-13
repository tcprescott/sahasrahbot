-- upgrade --
ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` INT;
-- downgrade --
ALTER TABLE `tournamentpresethistory` MODIFY COLUMN `episode_id` INT NOT NULL;
