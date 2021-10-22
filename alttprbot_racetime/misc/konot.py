from alttprbot import models


class KONOT(object):
    def __init__(self, rtgg_handler):
        self.rtgg_handler = rtgg_handler
        self.game: models.RacetimeKONOTGame = None
        self.segment: models.RaceTimeKONOTSegment = None

    @classmethod
    async def create_new(cls, category, rtgg_handler):
        konot = cls(rtgg_handler)
        konot.game = await models.RacetimeKONOTGame.create(category_slug=category)
        konot.segment = await models.RaceTimeKONOTSegment.create(
            racetime_room=rtgg_handler.data.get('name'),
            game_id=konot.game.id,
            segment_number=1
        )
        return konot

    @classmethod
    async def resume(cls, rtgg_handler):
        konot = cls(rtgg_handler)
        konot.segment = await models.RaceTimeKONOTSegment.get(racetime_room=rtgg_handler.data.get('name'))
        konot.game = await models.RacetimeKONOTGame.get(id=konot.segment.game_id)
        return konot

    @classmethod
    async def next_segment(cls, rtgg_handler, game: models.RacetimeKONOTGame, segment_number):
        konot = cls(rtgg_handler)
        konot.game = game
        konot.segment = await models.RaceTimeKONOTSegment.create(
            racetime_room=rtgg_handler.data.get('name'),
            game_id=konot.game.id,
            segment_number=segment_number
        )
        return konot

    def calc_advancing(self):
        if self.rtgg_handler.data['status']['value'] != 'finished':
            raise Exception("Race is not finished.  Cannot calculate advancing players.")

        entrants: list = self.rtgg_handler.data['entrants']

        # return a list of IDs, removing DNFs (and excluding the last place player)
        return [e['user']['id'] for e in entrants[:-1] if e['place'] is not None]

    async def create_next_room(self):
        if self.rtgg_handler.data['entrants_count'] <= 2:
            await self.rtgg_handler.send_message("This was the final race!  GG")
            return

        next_segment_number = self.segment.segment_number + 1

        params = {
            'invitational': True,
            'unlisted': False,
            'info': f"KONOT Series, Segment #{next_segment_number}",
            'start_delay': 15,
            'time_limit': 24,
            'streaming_required': self.rtgg_handler.data['streaming_required'],
            'auto_start': self.rtgg_handler.data['auto_start'],
            'allow_comments': self.rtgg_handler.data['allow_comments'],
            'hide_comments': self.rtgg_handler.data['hide_comments'],
            'allow_prerace_chat': self.rtgg_handler.data['allow_prerace_chat'],
            'allow_midrace_chat': self.rtgg_handler.data['allow_midrace_chat'],
            'allow_non_entrant_chat': self.rtgg_handler.data['allow_non_entrant_chat'],
            'chat_message_delay': 0,
            'team_race': False,
        }

        if self.rtgg_handler.data['goal']['custom']:
            params['custom_goal'] = self.rtgg_handler.data['goal']['name']
        else:
            params['goal'] = self.rtgg_handler.data['goal']['name']

        handler = await self.rtgg_handler.bot.startrace(**params)

        handler.konot = await KONOT.next_segment(handler, self.game, next_segment_number)

        for racetime_id in self.calc_advancing():
            await handler.invite_user(racetime_id)

        await self.rtgg_handler.send_message(
            f"Next race room at {self.rtgg_handler.bot.http_uri('/' + handler.data.get('name'))}")
