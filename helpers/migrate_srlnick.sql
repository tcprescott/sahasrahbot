INSERT into users (discord_user_id, twitch_name, rtgg_id, display_name) SELECT discord_user_id, twitch_name, rtgg_id, display_name FROM srlnick;

UPDATE asynctournamentrace
INNER JOIN users ON users.discord_user_id = asynctournamentrace.discord_user_id
SET asynctournamentrace.user_id = users.id;

UPDATE asynctournamentauditlog
INNER JOIN users ON users.discord_user_id = asynctournamentrace.discord_user_id
SET asynctournamentrace.user_id = users.id;

UPDATE asynctournamentwhitelist
INNER JOIN users ON users.discord_user_id = asynctournamentwhitelist.discord_user_id
SET asynctournamentwhitelist.user_id = users.id;