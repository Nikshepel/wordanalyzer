"""
The tests for the analyzer/arguments_parser.py module
"""
import io
import os
import pickle
import analyzer.bk_tree as bk
import unittest.mock
from similarity.damerau import Damerau
from pybktree import BKTree
from analyzer.configurator import Configurator


class ConfiguratorTest(unittest.TestCase):
    def setUp(self):
        self.args = ['-s', 'source', '-f', 'frequency']
        self.args_tree = self.args + ['-t', 'tree']
        self.source_file = 'source'
        self.tree_file = 'tree'
        self.frequency_file = 'frequency'
        self.configurator = Configurator(self.args)

        with open(self.source_file, 'w') as self.source:
            self.source.write('teststring')
        with open(self.frequency_file, 'w') as self.frequency:
            self.frequency.write('teststring')

    def tearDown(self):
        os.remove(self.source_file)
        os.remove(self.frequency_file)

        if os.path.isfile(self.tree_file):
            os.remove(self.tree_file)

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    def test_empty_input_words(self, error):
        args = []
        with self.assertRaises(SystemExit):
            configurator = Configurator(args)

        # Check that this error is what we expected
        self.assertTrue("No action requested, add -s/--source or -w/--words" in error.getvalue())

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    def test_empty_frequency_words(self, error):
        args = ['-w' 'word']
        with self.assertRaises(SystemExit):
            configurator = Configurator(args)

        # Check that this error is what we expected
        self.assertTrue("you must specify a file containing a list of frequency words" in error.getvalue())

    def test_default_values(self):
        args = ['-w', 'first', 'second', '-f', 'frequency']
        configurator = Configurator(args)
        parameters = configurator._get_parameters(args)

        # These parameters have no default value
        self.assertIsNone(parameters.count)
        self.assertIsNone(parameters.tree)
        self.assertIsNone(parameters.source)

        # These parameters are flags and are false by default
        self.assertFalse(parameters.clear_word)
        self.assertFalse(parameters.total_cost)
        self.assertFalse(parameters.verbose)

        # These parameters have a default value
        self.assertEqual(parameters.encoding, 'utf-8')
        self.assertEqual(parameters.destination, 'output.txt')
        self.assertEqual(parameters.number_corrected, 2)
        self.assertEqual(parameters.threshold, 2)
        self.assertEqual(parameters.distance, 1)
        self.assertEqual(parameters.similar_words, 4)

    def test_input_words(self):
        args = ['-w', 'first', 'second', '-f', 'frequency']
        parameters = Configurator(args)._parameters

        self.assertEqual(parameters.words, ['first', 'second'])
        self.assertEqual(parameters.frequency, 'frequency')

    def test_get_correct_words(self):
        args = ['-w', 'first', 'second', '-f', 'frequency', '-s', 'source']
        configurator = Configurator(args)

        # -w flag should cover the -s flag
        self.assertEqual(configurator.get_words(), ['first', 'second'])

    def test_get_destination(self):
        args = ['-w', 'first', 'second', '-f', 'frequency', '-d', 'new_file.txt']
        configurator = Configurator(args)

        self.assertEqual(configurator.get_destination(), 'new_file.txt')

    def test_get_frequency_words_wrong(self):
        args = ['-s' 'source', '-f' 'test']
        with self.assertRaises(FileNotFoundError):
            Configurator(args).get_frequency_words()

    @unittest.mock.patch('sys.stdout', open(os.devnull, 'w'))
    def test_get_frequency_words_correct(self):
        self.assertEqual(self.configurator.get_frequency_words(), ['teststring'])

    def test_get_words_sourcefile_wrong(self):
        args = ['-s' 'test', '-f' 'test']
        with self.assertRaises(FileNotFoundError):
            Configurator(args).get_words()

    @unittest.mock.patch('sys.stdout', open(os.devnull, 'w'))
    def test_get_words_sourcefile_correct(self):
        self.assertEqual(self.configurator.get_words(), ['teststring'])

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_tree_without_filename(self, output):
        configurator = Configurator(self.args)
        tree = configurator.get_tree()

        output_msg = output.getvalue()
        self.assertEqual(output_msg, f"Loading all words from {self.frequency_file}...\n"
                                     "The bk-tree is building...\n"
                                     "The bk-tree built successfully\n\n")
        self.assertEqual(tree.tree, BKTree(Damerau().distance, configurator.get_frequency_words()).tree)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_tree_without_existing_file_correct_tree(self, output):
        configurator = Configurator(self.args_tree)
        tree = configurator.get_tree()

        output_msg = output.getvalue()
        self.assertEqual(output_msg, f"Loading all words from {self.frequency_file}...\n"
                                     "The bk-tree is building...\n"
                                     "The bk-tree built successfully\n"
                                     f"The bk-tree is saving to {self.tree_file}...\n"
                                     "The bk-tree saved successfully\n\n")

        self.assertTrue(os.path.isfile(self.tree_file))
        self.assertEqual(BKTree(Damerau(), configurator.get_frequency_words()).tree, tree.tree)
        self.assertNotEqual(BKTree(Damerau(), ['abcdrasdsf']).tree, tree.tree)

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_tree_with_existing_empty_file(self, output, err):
        configurator = Configurator(self.args_tree)
        file = open(self.tree_file, 'w').close()
        tree = configurator.get_tree()

        output = output.getvalue()
        err = err.getvalue()
        self.assertEqual(output, f"Loading all words from {self.frequency_file}...\n"
                                 f"The bk-tree is loading from {self.tree_file}...\n"
                                 "The bk-tree is building...\n"
                                 "The bk-tree built successfully\n\n")
        self.assertEqual(err, "Error: The bk-tree file you specified is empty and can't be loaded\n")
        self.assertEqual(BKTree(Damerau(), configurator.get_frequency_words()).tree, tree.tree)
        self.assertNotEqual(BKTree(Damerau(), ['abcdrasdsf']).tree, tree.tree)

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_tree_with_existing_not_unpickling_file(self, output, err):
        configurator = Configurator(self.args_tree)
        with open(self.tree_file, 'w') as file:
            file.write("teststring")
        tree = configurator.get_tree()

        output = output.getvalue()
        err = err.getvalue()
        self.assertEqual(output, f"Loading all words from {self.frequency_file}...\n"
                                 f"The bk-tree is loading from {self.tree_file}...\n"
                                 "The bk-tree is building...\n"
                                 "The bk-tree built successfully\n\n")
        self.assertEqual(err,
                         "Error: This file of the bk-tree structure doesn't contain any bk-tree structure actually\n")
        self.assertEqual(BKTree(Damerau(), configurator.get_frequency_words()).tree, tree.tree)
        self.assertNotEqual(BKTree(Damerau(), ['abcdrasdsf']).tree, tree.tree)

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_tree_with_existing_wrong_pickling_file(self, output, err):
        configurator = Configurator(self.args_tree)
        with open(self.tree_file, 'wb') as file:
            pickle.dump("teststring", file)
        tree = configurator.get_tree()

        output = output.getvalue()
        err = err.getvalue()
        self.assertEqual(output, f"Loading all words from {self.frequency_file}...\n"
                                 f"The bk-tree is loading from {self.tree_file}...\n"
                                 "The bk-tree is building...\n"
                                 "The bk-tree built successfully\n\n")
        self.assertEqual(err,
                         "Error: You're trying to load from the file not a BK-tree object\n")
        self.assertEqual(BKTree(Damerau(), configurator.get_frequency_words()).tree, tree.tree)
        self.assertNotEqual(BKTree(Damerau(), ['abcdrasdsf']).tree, tree.tree)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_get_tree_correct_load(self, output):
        configurator = Configurator(self.args_tree)
        tree1 = bk.BuildBKTree.build_tree(["teststring"])
        with open(self.tree_file, 'wb') as file:
            pickle.dump(tree1, file)

        tree2 = configurator.get_tree()

        output = output.getvalue()
        self.assertEqual(output, f"Loading all words from {self.frequency_file}...\n"
                                 f"The bk-tree is loading from {self.tree_file}...\n"
                                 "The bk-tree loaded successfully\n\n")

        self.assertEqual(tree1.tree, tree2.tree)
        self.assertNotEqual(BKTree(Damerau(), ['abcdrasdsf']).tree, tree1.tree)
