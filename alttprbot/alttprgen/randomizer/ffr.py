import random


def roll_ffr(flags):
    seed = ('%008x' % random.randrange(16**8)).upper()
    return seed, f"https://finalfantasyrandomizer.com/Randomize?s={seed}&f={flags}"
