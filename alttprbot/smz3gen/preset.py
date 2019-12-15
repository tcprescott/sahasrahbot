import pyz3r

async def get_preset(preset, tournament=True, morph='randomized'):
    seed = await pyz3r.smz3(
        settings={
            'logic': 'NoMajorGlitches',
            'sm_logic': 'Casual' if preset == 'normal' else 'Tournament',
            'difficulty': 'normal',
            'variation': 'combo',
            'mode': 'open',
            'goal': 'ganon',
            'weapons': '',
            'morph': morph,
            'heart_speed': 'half',
            'sram_trace': 'false',
            'menu_speed': 'normal',
            'debug': False,
            'tournament': tournament
        }
    )
    return seed
