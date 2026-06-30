import random
import string


def generate_random_string(length: int):
    """
    Generate a random string of the desired length.

    :param length: The length of the string to generate.
    :return: The generated string.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
