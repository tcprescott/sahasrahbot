from .core import SahasrahBotCoreHandler
from alttprbot.tournament import alttpr
from alttprbot.database import tournament_results


class GameHandler(SahasrahBotCoreHandler):
    async def race_data(self, data):
        self.data = data.get('race')

        if self.data.get('status', {}).get('value') in ['open', 'invitational']:
            await self.intro()

        pending_entrants = [e for e in self.data['entrants'] if e.get('status', {}).get('value', {}) == 'requested']
        for entrant in pending_entrants:
            if self.tournament:
                if entrant['user']['id'] in self.tournament.player_racetime_ids:
                    await self.accept_request(entrant['user']['id'])

                elif await alttpr.can_gatekeep(entrant['user']['id'], self.data['name']):
                    await self.accept_request(entrant['user']['id'])
                    await self.add_monitor(entrant['user']['id'])

    async def begin(self):
        if self.tournament is None:
            race = await tournament_results.get_active_tournament_race(self.data.get('name'))
            if race:
                self.tournament = await alttpr.TournamentRace.construct(episodeid=race['episode_id'])

    async def intro(self):
        pass

    async def ex_help(self, args, message):
        await self.send_message("I have no commands for this category.")
