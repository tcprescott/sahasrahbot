import random


def roll_aosr(logic, panther, boss, kicker):
    seed = random.randint(-2147483648, 2147483647)
    return f"https://aosrando.surge.sh/?seed={seed}&logic={logic}&panther={panther}&boss={boss}&kicker={kicker}"
