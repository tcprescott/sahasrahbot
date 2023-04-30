import random
import string

def generate_random_string(length: int):
    """
    Generate a random string of the desired length.

    :param length: The length of the string to generate.
    :return: The generated string.
    """
    chars = string.ascii_letters + string.digits

    # generate the random string of the desired length
    random_string = ''
    for i in range(length):
        random_string += random.choice(chars)

    return random_string
