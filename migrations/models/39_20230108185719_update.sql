-- upgrade --
ALTER TABLE `ranked_choice_candidate` CHANGE candidate_name name VARCHAR(200);
-- downgrade --
ALTER TABLE `ranked_choice_candidate` CHANGE name candidate_name VARCHAR(200);
