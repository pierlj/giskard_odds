import os
import sys
import json

import unittest

sys.path.insert(1, "backend/")
print(os.path.abspath("../"))

from odd_computation import compute_odds, compute_path_length, compute_encounters
from utils import * 


EXAMPLES_MAIN_FOLDER = "examples/"

class TestGraphUtils(unittest.TestCase):

    def test_compute_path_length(self):
        millennium_dict = safe_load_json(os.path.join(EXAMPLES_MAIN_FOLDER, 'example1/millennium-falcon.json'), FALCON_SCHEMA)
        universe_graph = build_unvierse_graph(os.path.join(EXAMPLES_MAIN_FOLDER, 'example1/universe.db'), millennium_dict)
        self.assertEqual(compute_path_length(['Tatooine', 'Hoth'], universe_graph, 6), (6, 6, 0))
        self.assertEqual(compute_path_length(['Tatooine', 'Hoth'], universe_graph, 8), (6, 6, 0))
        self.assertEqual(compute_path_length(['Tatooine', 'Hoth', 'Endor'], universe_graph, 6), (8, 7, 1))
        self.assertEqual(compute_path_length(['Tatooine', 'Hoth', 'Tatooine', 'Hoth', 'Tatooine', 'Hoth'], universe_graph, 6), (34, 30, 4))
        
    def test_compute_encounters(self):
        self.assertEqual(compute_encounters(['Tatooine', 'Hoth'], [(0,0),(6,6)], {'Tatooine': {0,1,2}, 'Hoth': {4,5,6}}), 2)
        self.assertEqual(compute_encounters(['Tatooine', 'Hoth', 'Endor'], [(0,0),(6,7),(8,8)], {'Hoth': {6,7,8}}), 2)
        self.assertEqual(compute_encounters(['Tatooine', 'Hoth', 'Endor'], [(0,1),(7,8),(9,9)], {'Hoth': {6,7,8}}), 2)
        self.assertEqual(compute_encounters(['Tatooine', 'Hoth', 'Endor'], [(0,2),(8,9),(10,10)], {'Hoth': {6,7,8}}), 1)
        self.assertEqual(compute_encounters(['Tatooine', 'Dagobah', 'Hoth', 'Endor'], [(0,0),(6,7),(8,8),(9,9)], {'Hoth': {6,7,8}}), 1)
        self.assertEqual(compute_encounters(['Tatooine', 'Dagobah', 'Hoth', 'Endor'], [(0,1),(7,8),(9,9),(10,10)], {'Hoth': {6,7,8}}), 0)

    def test_correctness(self):
        n_examples = 0
        success = 0

        for example_folder in os.listdir(EXAMPLES_MAIN_FOLDER):
            n_examples += 1
            with open(os.path.join(EXAMPLES_MAIN_FOLDER, example_folder, "answer.json")) as f:
                answer = json.load(f)["odds"]

            odds, _ = compute_odds(
                os.path.join(EXAMPLES_MAIN_FOLDER, example_folder, "millennium-falcon.json"),
                os.path.join(EXAMPLES_MAIN_FOLDER, example_folder, "empire.json"),
                verbose=False,
            )
            self.assertAlmostEqual(odds / 100, answer, places=5)

   

if __name__ == "__main__":
    
    unittest.main()


