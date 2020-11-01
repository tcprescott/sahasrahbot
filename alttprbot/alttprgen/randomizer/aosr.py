import random


def roll_aosr(logic, panther, boss, weight, kicker, levelexp):
    seed = random.randint(-2147483648, 2147483647)
    return seed, f"https://aosrando.surge.sh/?seed={seed}&logic={logic}&panther={panther}&boss={boss}&weight={weight}&kicker={kicker}&levelexp={levelexp}"
