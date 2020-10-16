import random


def roll_ffr(flags):
    seed = ('%008x' % random.randrange(16**8)).upper()
    return f"https://finalfantasyrandomizer.com/Randomize?s={seed}&f={flags}"
