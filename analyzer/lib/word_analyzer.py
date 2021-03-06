"""
This module provides WordAnalyzer class that is a wrapper for words dictionary and any functions for
working with them.
"""

import sys
import analyzer.lib.configurator as cfg
from copy import deepcopy
from analyzer.lib.text_splitter import TextSplitter
from analyzer.lib.methods import (get_indices_incorrect_symbols, leet_transform, factorize, print_results, get_patterns,
                                  delete_duplicates)
from nltk.stem import SnowballStemmer


class WordAnalyzer:
    @staticmethod
    def build(configurator: cfg.Configurator):
        analyzer = WordAnalyzer()
        analyzer.words = configurator.get_words(verbose=True)
        analyzer.frequency_words = configurator.get_frequency_words(verbose=True)
        analyzer.splitter = TextSplitter(analyzer.frequency_words)
        analyzer.tree = configurator.get_tree()
        analyzer.mode = configurator.get_mode()
        analyzer.verbose = configurator.get_verbose()

        # This flag specifies that's need add extra information with a word when analyzing words
        analyzer.verbose_file = False

        # If the word isn't in the dictionary, then its cost is default_cost
        analyzer.default_cost = 1000

        # How many similar words will be returned by get_similar_words method
        analyzer.number_similar_words = configurator.get_configuration_values()['similar_words']
        # What distance will be used to search for similar words
        analyzer.distance = configurator.get_configuration_values()['distance']
        # How many parts will be spliced in the get_correct_words method
        analyzer.threshold = configurator.get_configuration_values()['threshold']
        # How many words will be returned by get_correct_words method
        analyzer.number_of_corrected_words = configurator.get_configuration_values()['number_corrected']

        analyzer.max_len = max(len(x) for x in analyzer.words)
        # Define dictionary with values like (number: list_of_divisors).
        # There are defined all numbers from 1 to max length of all words.
        # It's necessary to improve efficiency, because divisors won't calculated again for same number
        analyzer.divisors = dict((number, factorize(number)) for number in range(1, analyzer.max_len + 1))

        return analyzer

    def analyze(self, words: list = None):
        """
        This method runs a necessary method depending on the mode that a user chosen. Also, this method determines
        the text which will be printed in the stdout or a file.

        :param words: a list of words which will be processed. If it isn't specified, that list will be taken
                      from the Configurator
        :param destination: the name of a file where you want to save results. If it isn't specified, that filename will
                            be taken from the Configurator
        """
        if words is None:
            words = self.words

        # Calculating mode of work
        mode = self.mode
        verbose = self.verbose
        patterns = get_patterns(mode, verbose)
        files = {filename: sys.stdout if filename == "STDOUT" else open(filename, "w")
                 for filename in set(mode.values())}

        for word in words:
            clear = corrects = None
            arguments = {filename: [] for filename in set(mode.values())}

            if cfg.MODE_COST in mode:
                cost = self._get_total_cost(word)
                filename = mode[cfg.MODE_COST]
                arguments[filename].append(cost)

            if cfg.MODE_CLEAR in mode:
                clear = self._get_clear_word(word)
                filename = mode[cfg.MODE_CLEAR]
                arguments[filename].append(clear)

            if cfg.MODE_CORRECT in mode:
                if clear:
                    corrects = self._get_correct_words(word, clear_word=clear)
                else:
                    corrects = self._get_correct_words(word)

                filename = mode[cfg.MODE_CORRECT]
                arguments[filename].append(corrects)

            if cfg.MODE_BASIC in mode:
                basics = set()
                if not corrects:
                    corrects = self._get_correct_words(word, clear_word=clear)
                for correct in corrects:
                    basics |= self._get_base_parts(correct)

                filename = mode[cfg.MODE_BASIC]
                arguments[filename].append(basics)

            for filename in set(mode.values()):
                pattern = patterns[filename]
                args = arguments[filename]
                file = files[filename]

                print_results(word, pattern, args, file, verbose)

        for filename, file in files.items():
            if filename != "STDOUT":
                file.close()
                delete_duplicates(filename)

    def _get_total_cost(self, text: str) -> int:
        """
        Calculate total cost of the text based on cost of the each word
        :param text: the text without spaces
        :return: total sum of costs
        """

        return sum([self.splitter.word_cost.get(word, self.default_cost) for word in self.splitter.split(text)])

    def _get_clear_word(self, word: str) -> str:
        """
        This function iterates through possible combinations of indices, which were obtained from
        get_indices_incorrect_symbols. Function returns the cheapest found word among possible combinations.

        :param word: word that will be cleared
        :return: the cheapest cleared word
        """

        # Get all indices of incorrect symbols
        indices = get_indices_incorrect_symbols(word)

        # Define an empty combination. It's important in order to check the cost of the word without changes
        all_combinations = [set()]
        # A cleaned word will be calculated based on this cost
        minimal_cost, cleared_word = 9e999, ''

        # The idea is absolutely simple: we need to find the optimal list of indexes which will help us to calculate
        # the cheapest correct word based on leet_transform function. Starting with an empty list, add new calculated
        # index each iteration. Number of new indexes sets may be limited. Return the cheapest of all calculated words.
        for key in range(len(indices) + 1):
            costs_indexes = []

            # Iterate over all calculated indexes sets and calculate total cost for each word returned by
            # leet_transform function
            for combination in all_combinations:
                prepared_str = leet_transform(word, combination)
                total_cost = self._get_total_cost(prepared_str.lower())
                costs_indexes.append([total_cost, set(combination), prepared_str])

            # Sort all indexes sets by their cost
            costs_indexes.sort()

            # The first set is the cheapest. Redetermine minimal cost.
            cost, combination, min_word = costs_indexes[0]
            if cost < minimal_cost:
                minimal_cost = cost
                cleared_word = min_word

            # Take only first 5 sets of all list
            costs_indexes = costs_indexes[:5]
            if not costs_indexes:
                break

            # Calculate new sets of indexes by adding another one
            all_combinations = set()
            for cost_index in costs_indexes:
                for index in indices:
                    # We need to add indexes from original list which aren't in the redetermined set
                    if index not in cost_index[1]:
                        new_combination = deepcopy(cost_index[1])
                        new_combination.add(index)

                        # It's necessary to convert set to tuple and add it to the final set
                        # in order to get rid of duplicates
                        new_combination = tuple(new_combination)
                        all_combinations.add(new_combination)

        return cleared_word

    def _detect_repeated_word(self, word: str) -> str:
        """
        This method detects that some part is repeated in the word and returns that part.
        If any part is not found, returns empty string.

        :param word: word which will be checked
        :return: repeated word
        """

        if not len(word):
            return None

        # Get list of divisors for word's length
        divisors = self.divisors.get(len(word))
        if not divisors:
            return None

        # Split the word to the number of parts determined by the divisor. If the part is repeated,
        # then all next parts equal it.
        for divisor in divisors:
            repeat = True
            part = word[:divisor]

            for start in range(0, len(word), divisor):
                if word[start:start + divisor] != part:
                    repeat = False
                    break

            if repeat:
                return part

    def _get_similar_words(self, word: str) -> list:
        """
        This function finds all similar words to passed word depending on the Damerau's distance. Function returns
        only first number_similar_words (by default, 4) words of the most similar words.

        :param word: function will find similar words to this word
        :return: list of the most similar words
        """

        number_similar_words = self.number_similar_words
        distance = self.distance

        found_words = self.tree.find(word, distance)

        arr = [[self._get_total_cost(it[1]), it[1]] for it in found_words]
        if arr:
            arr = sorted(arr)[:number_similar_words]
            return [it[1] for it in arr]
        else:
            return None

    def _get_correct_words(self, word: str, clear_word: str = None) -> set:
        """
        This function clears passed word, then splits it to some parts and in turn splice these parts into one word,
        trying to find the cheapest for each. How many parts will be spliced is determined by the threshold argument.
        By changing threshold parameter, you can reach at an optimal correcting. After correcting many corrected
        words will be returned. How many determined by number_of_corrected_words. You can change that parameter
        in order to build optimal list of corrected words.

        :param word: word that will be corrected
        :return: list of corrected words
        """

        minimum_parts = 2
        threshold = self.threshold
        number_of_corrected_words = self.number_of_corrected_words

        word = clear_word if clear_word else self._get_clear_word(word)

        repeated_word = self._detect_repeated_word(word)
        if repeated_word:
            word = repeated_word

        parts = self.splitter.split(word)
        evaluated_words = []

        def replace_correcting_parts(parts: list, similar_words: list, indices: list) -> list:
            """
            This function receives parts - list of parts of a word. Some of these parts whose indices are passed as
            third argument splice into one word and similar words to that word pass to this function.
            Indices - indices of those parts of a word that were spliced into one. So, this function pastes
            one of the similar words to the places indicated by indices, then that all splices with the rest
            parts of a word and then it will be evaluated. The cost of the full spliced word with this word will be
            appended into the list. The list containing all these similar spliced words with their cost
            will be returned.

            :param parts: list of parts of a word
            :param similar_words: list of similar to a word which will be replaced
            :param indices: indices of those parts of a word that were spliced into one
            :return: list of (cost of full spliced word, this word)
            """

            i, j = indices
            full_words_with_cost = []
            for similar_word in similar_words:
                full_word = ''.join(parts[:i] + [similar_word] + parts[j + 1:])
                cost = self._get_total_cost(full_word)
                full_words_with_cost.append([cost, full_word])

            return full_words_with_cost

        # If after splitting the count of parts isn't enough
        if len(parts) < minimum_parts:
            arr = []
            for part in parts:
                similar = self._get_similar_words(part)
                if similar:
                    arr.extend(similar)

            arr = sorted(evaluated_words)[:number_of_corrected_words]
            if word:
                arr.append(word)
            return set(arr)

        for i in range(len(parts)):
            # That value will decrease
            max_range = threshold if threshold <= len(parts) - i else len(parts) - i

            for j in range(i + minimum_parts, max_range + i + 1):
                spliced_word = ''.join(parts[i:j])
                similar_words = self._get_similar_words(spliced_word)

                if similar_words:
                    full_words = replace_correcting_parts(parts, similar_words, (i, j - 1))
                    evaluated_words.extend(full_words)

        arr = sorted(evaluated_words)[:number_of_corrected_words]
        if word:
            arr.append([0, word])

        return set(it[1] for it in arr)

    def _get_base_parts(self, word: str) -> set:
        """
        This function identifies the base parts of a word, applies the stemming to them and returns a list of base words.
        If the destination is specified, then saves the list into this file.

        :param words: a list of words which will be processed
        :param splitter: an instance of the TextSplitter to split a word to parts
        :param destination:  a filename that you want to save a list to
        :return: a list of base words
        """
        stemmer = SnowballStemmer('english')
        basics = set()
        splitter = self.splitter

        for part in splitter.split(word):
            part = part.lower()
            cost = splitter.word_cost.get(part)
            if cost:
                basics.add(stemmer.stem(part).lower())

        return basics
