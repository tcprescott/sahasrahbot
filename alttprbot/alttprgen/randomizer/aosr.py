import random


def roll_aosr(**kwargs):
    seed = random.randint(-2147483648, 2147483647)
    flags = [f"{key}={val}" for (key, val) in kwargs.items()]
    return seed, f"https://aosrando.surge.sh/?seed={seed}&{'&'.join(flags)}"
