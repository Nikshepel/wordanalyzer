import unittest
import os
import pickle
from analyzer.lib.bk_tree import BuildBKTree, BKTree, WordsBKTreeError, FileBKTreeError, WrongTreeError
from pyxdameraulevenshtein import damerau_levenshtein_distance as distance


class BuildBKTreeTest(unittest.TestCase):
    def setUp(self):
        self.filename = 'test'
        self.words = ['first', 'second']
        self.distance = distance

    def tearDown(self):
        if os.path.isfile(self.filename):
            os.remove(self.filename)

    def test_build_tree_correct(self):
        self.assertEqual(BuildBKTree.build_tree(self.words).tree, BKTree(self.distance, self.words).tree)
        self.assertNotEqual(BuildBKTree.build_tree(['5555']).tree, BKTree(self.distance, self.words).tree)

    def test_build_tree_incorrect_words(self):
        with self.assertRaises(WordsBKTreeError):
            BuildBKTree.build_tree([])
        with self.assertRaises(WordsBKTreeError):
            BuildBKTree.build_tree(None)

    def test_save_tree_incorrect_filename(self):
        with self.assertRaises(FileBKTreeError):
            BuildBKTree.save_tree(None, BuildBKTree.build_tree(['123']))
        with self.assertRaises(FileBKTreeError):
            BuildBKTree.save_tree("", BuildBKTree.build_tree(['123']))

    def test_save_tree_correct_filename(self):
        BuildBKTree.save_tree(self.filename, BuildBKTree.build_tree(['123']))

        self.assertTrue(os.path.isfile(self.filename))
        self.assertTrue(os.stat(self.filename).st_size != 0)

    def test_save_tree_not_empty_file(self):
        with open(self.filename, 'w') as file:
            file.write('test')

        with self.assertRaises(FileBKTreeError):
            BuildBKTree.save_tree(self.filename, BuildBKTree.build_tree(['123']))

    def test_save_tree_incorrect_tree(self):
        with self.assertRaises(WrongTreeError):
            BuildBKTree.save_tree(self.filename, '123')
        with self.assertRaises(WrongTreeError):
            BuildBKTree.save_tree(self.filename, [])
        with self.assertRaises(WrongTreeError):
            BuildBKTree.save_tree(self.filename, None)

    def test_load_tree_incorrect_filename(self):
        with self.assertRaises(FileBKTreeError):
            BuildBKTree.load_tree(self.filename)
        with self.assertRaises(FileBKTreeError):
            BuildBKTree.load_tree('')
        with self.assertRaises(FileBKTreeError):
            BuildBKTree.load_tree(None)

    def test_load_tree_unpickling_file(self):
        with open(self.filename, 'w') as file:
            file.write('test')

        with self.assertRaises(FileBKTreeError):
            BuildBKTree.load_tree(self.filename)

    def test_load_tree_empty_file(self):
        open(self.filename, 'w').close()

        with self.assertRaises(FileBKTreeError):
            BuildBKTree.load_tree(self.filename)

    def test_load_tree_notinstance_file(self):
        with open(self.filename, 'wb') as file:
            pickle.dump('teststring', file)

        with self.assertRaises(WrongTreeError):
            BuildBKTree.load_tree(self.filename)

    def test_tree_correct_work(self):
        tree1 = BuildBKTree.build_tree(self.words)
        BuildBKTree.save_tree(self.filename, tree1)

        with open(self.filename, 'rb'):
            tree2 = BuildBKTree.load_tree(self.filename)

        self.assertEqual(tree1.tree, tree2.tree)
