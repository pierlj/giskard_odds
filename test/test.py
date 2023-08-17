import os
import sys
import json
import logging

sys.path.insert(1, "backend/")
print(os.path.abspath("../"))

from odd_computation import compute_odds


logger = logging.getLogger(name="R2D2_Test")
logging.basicConfig(level=logging.INFO)

EXAMPLES_MAIN_FOLDER = "examples/"
n_examples = 0
success = 0

for example_folder in os.listdir(EXAMPLES_MAIN_FOLDER):
    n_examples += 1
    logger.info("Running test on {}".format(example_folder))
    with open(os.path.join(EXAMPLES_MAIN_FOLDER, example_folder, "answer.json")) as f:
        answer = json.load(f)["odds"]

    odds, _ = compute_odds(
        os.path.join(EXAMPLES_MAIN_FOLDER, example_folder, "millennium-falcon.json"),
        os.path.join(EXAMPLES_MAIN_FOLDER, example_folder, "empire.json"),
        verbose=False,
    )
    logger.info("Computed odds: {}, answer: {}".format(odds / 100, answer))
    if abs(odds / 100 - answer) <= 1e-5:
        success += 1

logger.info("Correctness test passed with {}%".format(success / n_examples * 100))
