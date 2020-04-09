"""
This module implements loading words from the file
"""

import codecs
from random import sample
from os import stat


def load_words(words_filename, count=None):
    """
    :param words_filename: str - filename
    :param count: int - count of words which will be processed
    :return: list(str) - list of loaded words
    """

    if stat(words_filename).st_size == 0:
        raise EmptyFileError()

    if count == 0:
        raise ValueError("Count can't be 0")

    with codecs.open(words_filename, 'r', 'ANSI') as f:
        data = f.read().splitlines()

    return sample(data, count) if count is not None else data


class EmptyFileError(Exception):
    """
    The error will be raised when empty file is passed to input
    """
    def __init__(self):
        self.text = "The specified file is empty!"