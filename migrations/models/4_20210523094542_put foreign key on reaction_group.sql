-- upgrade --
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` INT NOT NULL;
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` INT NOT NULL;
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` INT NOT NULL;
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` INT NOT NULL;
ALTER TABLE `reaction_role` ADD CONSTRAINT `fk_reaction_reaction_b36466fe` FOREIGN KEY (`reaction_group_id`) REFERENCES `reaction_group` (`id`) ON DELETE CASCADE;
-- downgrade --
ALTER TABLE `reaction_role` DROP FOREIGN KEY `fk_reaction_reaction_b36466fe`;
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` BIGINT;
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` BIGINT;
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` BIGINT;
ALTER TABLE `reaction_role` MODIFY COLUMN `reaction_group_id` BIGINT;
