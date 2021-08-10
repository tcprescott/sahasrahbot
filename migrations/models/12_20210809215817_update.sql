-- upgrade --
ALTER TABLE `racetimekonotsegment` DROP FOREIGN KEY `fk_racetime_racetime_282bffe9`;
ALTER TABLE `racetimekonotsegment` MODIFY COLUMN `game_id` INT NOT NULL;
-- downgrade --
ALTER TABLE `racetimekonotsegment` MODIFY COLUMN `game_id` INT NOT NULL;
ALTER TABLE `racetimekonotsegment` ADD CONSTRAINT `fk_racetime_racetime_282bffe9` FOREIGN KEY (`game_id`) REFERENCES `racetimekonotgame` (`id`) ON DELETE CASCADE;
