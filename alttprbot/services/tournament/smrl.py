"""``SMRLPlayoffsOrchestrator`` — the Super Metroid Random League playoffs, decomposed.

Mirrors the legacy ``smrl_playoff.SMRLPlayoffs`` (which extended the base ``TournamentRace``,
not the ALTTPR family): a Super Metroid event whose game is chosen via a settings-submission
form, then rolled on either the VARIA or DASH randomizer. Unlike the ALTTPR events there is
no seed embed — the roll just whispers the seed URL to the race room and sets the bot
race-info. It therefore extends the **base** :class:`TournamentOrchestrator` and overrides:

- ``process_race`` — generate the SM seed (VARIA / DASH) from the submitted settings, persist
  the permalink, announce.
- ``send_room_welcome`` — a single pinned welcome message carrying the "Roll Tournament Seed" action.
- ``before_room_creation`` — gate room creation on submitted settings (send a reminder otherwise).
- ``process_submission_form`` — map the submitted game number to a randomizer/preset, persist it,
  and confirm via the presenter.

``SMRL_SUBMISSION_FORM`` (the JSON form schema the web API renders) moves onto the definition.
"""

from pyz3r.smvaria import SuperMetroidVaria

from alttprbot.repositories import TournamentGamesRepository, TournamentResultsRepository
from alttprbot.services.seedgen.randomizer import smdash
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition

# The settings-submission form schema (rendered by the JSON submission API). Static data, so
# it lives on the definition rather than as an instance property (legacy: SMRLPlayoffs.submission_form).
SMRL_SUBMISSION_FORM = [
    {
        'key': 'game',
        'label': 'Game #',
        'settings': {
            '1': 'Power',
            '2': 'Varia',
            '3': 'Gravity',
            '4': 'Game 4',
            '5': 'Game 5',
        },
    },
    {
        'key': 'preset',
        'label': 'Preset (games 4 & 5 only)',
        'settings': {
            'RLS4W2': 'Countdown, Full Area, Vanilla Bosses (week 2)',
            'RLS4W3': 'Major/Minor, Full Area, Boss Shuffle (week 3)',
            'RLS4P1': 'Countdown, Vanilla Area, Boss Shuffle (week 4 equivalent)',
            'classic_mm': 'Classic DASH',
            'RLS4P2': 'Chozo, Full Area, Vanilla Bosses',
        },
    },
]

SMRL_DEFINITION = TournamentDefinition(
    event_slug="smrl",
    racetime_category="smr",
    racetime_goal="Beat the game",
    guild_id=500362417629560881,
    audit_channel_id=1080994224880750682,
    helper_role_ids=[500363025958567948, 501810831504179250, 504725352745140224],
    submission_form=SMRL_SUBMISSION_FORM,
)


class SMRLPlayoffsOrchestrator(TournamentOrchestrator):
    async def process_race(self, args, message) -> bool:
        room = self.room.name
        await self.racetime.send_message(
            room,
            "Generating game, please wait.  If nothing happens after a minute, contact Synack.",
        )

        await self.update_data()

        randomizer = self.tournament_game.settings["randomizer"]
        preset = self.tournament_game.settings["preset"]

        permalink = None
        if randomizer == "smvaria":
            seed = await SuperMetroidVaria.create(
                settings_preset=preset, skills_preset="Season_Races", race=True
            )
            await self.racetime.send_message(room, seed.url)
            await self.racetime.set_bot_raceinfo(room, seed.url)
            permalink = seed.url
        elif randomizer == "smdash":
            seed = await smdash.create_smdash(mode=preset)
            await self.racetime.send_message(room, seed)
            await self.racetime.set_bot_raceinfo(room, seed)
            permalink = seed

        await TournamentResultsRepository.create_or_update_with_permalink(
            srl_id=room,
            defaults={"episode_id": self.episodeid, "event": self.event_slug, "spoiler": None},
            permalink=permalink,
        )

        await self.racetime.send_message(room, "Seed has been generated!")
        return True

    async def send_room_welcome(self) -> None:
        await self.racetime.send_pinned_action(
            self.room.name,
            (
                "Welcome. Use !tournamentrace (without any arguments) to roll your seed!  This "
                "should be done about 5 minutes prior to the start of your race.  You do NOT need "
                "to wait for your setup helper to do this or start your race, they will appear "
                "later to setup the stream."
            ),
            label="Roll Tournament Seed",
            help_text=(
                "Create a seed for this specific tournament race.  This should only be done "
                "shortly before the race starts."
            ),
            message="!tournamentrace",
        )

    async def before_room_creation(self) -> bool:
        if self.tournament_game is None or self.tournament_game.settings is None:
            await self.send_race_submission_form(warning=True)
            return False
        return True

    async def process_submission_form(self, payload, submitted_by) -> None:
        game_number = int(payload["game"])

        if game_number == 1:
            randomizer, preset = "smvaria", "RLS4W5"
        elif game_number == 2:
            randomizer, preset = "smdash", "recall_mm"
        elif game_number == 3:
            randomizer, preset = "smvaria", "RLS4GS"
        elif game_number in (4, 5):
            preset = payload["preset"]
            randomizer = "smdash" if preset == "classic_mm" else "smvaria"

        settings = {"randomizer": randomizer, "preset": preset}
        await TournamentGamesRepository.upsert_by_episode_id(
            episode_id=self.episodeid,
            defaults={"settings": settings, "event": self.event_slug, "game_number": game_number},
        )

        await self.presenter.send_submission_confirmation(
            versus=self.versus,
            episode_id=self.episodeid,
            event=self.event_slug,
            game_number=game_number,
            randomizer=randomizer,
            preset=preset,
            submitted_by=submitted_by,
            players=[(p.name, p.discord_user_id) for p in self.players],
        )
