from tortoise import BaseDBAsyncClient

# Elections overhaul: voting methods, drafts, closing times and stored counts.
# Only adds columns. Existing elections become ranked (STV) elections; closed ones
# keep their pyrankvote text in `results` and get `tally` on first view.


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_election` ADD `method` VARCHAR(16) NOT NULL DEFAULT 'stv';
        ALTER TABLE `ranked_choice_election` ADD `status` VARCHAR(16) NOT NULL DEFAULT 'open';
        ALTER TABLE `ranked_choice_election` ADD `closes_at` DATETIME(6);
        ALTER TABLE `ranked_choice_election` ADD `closed_at` DATETIME(6);
        ALTER TABLE `ranked_choice_election` ADD `tally` JSON;
        UPDATE `ranked_choice_election` SET `status` = 'closed', `closed_at` = `updated` WHERE `active` = 0;
        ALTER TABLE `ranked_choice_candidate` ADD `position` INT NOT NULL DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_candidate` DROP COLUMN `position`;
        ALTER TABLE `ranked_choice_election` DROP COLUMN `tally`;
        ALTER TABLE `ranked_choice_election` DROP COLUMN `closed_at`;
        ALTER TABLE `ranked_choice_election` DROP COLUMN `closes_at`;
        ALTER TABLE `ranked_choice_election` DROP COLUMN `status`;
        ALTER TABLE `ranked_choice_election` DROP COLUMN `method`;"""
