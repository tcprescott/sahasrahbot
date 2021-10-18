-- upgrade --
ALTER TABLE `presetnamespaces` CHANGE namespace name VARCHAR(50);
-- downgrade --
ALTER TABLE `presetnamespaces` CHANGE name namespace VARCHAR(50);
