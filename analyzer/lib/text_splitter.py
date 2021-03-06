"""
This module provides the class for splitting a text without spaces. You need just create instance of that class
and call the split function.
"""
from math import log


class TextSplitter:
    def __init__(self, words: list):
        """
        Builds words cost dictionary using the list of words passed to constructor
        :param words: the list of words is ordered by frequency usage
        """

        # Check that list is not empty or None
        if words == [] or words is None:
            raise ValueError("The list of words is empty or None")

        # It's necessary the each element is str type in the list
        if not all(isinstance(word, str) for word in words):
            raise TypeError("The list of words has a non string type element")

        # Build a cost dictionary, assuming Zipf's law
        self.word_cost = dict((word, log((number + 1) * log(len(words)))) for number, word in enumerate(words))
        self.max_len = max(len(x) for x in words)

    def split(self, text: str):
        """
        Split the text without spaces. Returns array of split words
        :param text: text you need to split
        :return: list of split words
        """

        # It was decided that it's necessary to deliberately refuse to check for incorrect characters in the
        # text to increase performance. Also, this check must be performed before passing the text to the
        # function as intended by the author.

        if not isinstance(text, str):
            raise TypeError("Text must be str type")

        # Find the best match for the i first characters, assuming cost has
        # been built for the i-1 first characters.
        # Returns a pair (match_cost, match_length).
        def best_match(index):
            candidates = enumerate(reversed(cost[max(0, index - self.max_len):index]))
            costs = list(((match_cost + self.word_cost.get(text[index - match_length - 1:index].lower(), 9e999),
                           match_length + 1) for match_length, match_cost in candidates))

            return min(costs)

        # Build the cost array.
        cost = [0]
        for i in range(1, len(text) + 1):
            match_cost, match_length = best_match(i)
            cost.append(match_cost)

        # Backtrack to recover the minimal-cost string.
        out = []
        i = len(text)
        while i > 0:
            match_cost, match_length = best_match(i)
            assert match_cost == cost[i]

            out.append(text[i - match_length:i])

            i -= match_length
        return list(reversed(out))
