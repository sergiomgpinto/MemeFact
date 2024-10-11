import argparse
import traceback
from typing import List
from data.schemas import Meme
from variants.baseline import BaselineVariant
from variants.rag import RagVariant
from variants.debate import DebateVariant
from variants.rlhf import RlhfVariant
from utils.helpers import load_config


class MemeFactRunner:
    def __init__(self, config_file: str):
        self.config = load_config(config_file)
        self.variants = {
            'baseline': BaselineVariant(self.config),
            'rag': RagVariant(self.config),
            'debate': DebateVariant(self.config),
            'rlhf': RlhfVariant(self.config)
        }

    def run(self, args) -> List[Meme]:
        return self.variants[args['variant']].run(args)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate a meme explanation for a PolitiFact article.")

    parser.add_argument("-p", "--politifact", required=True, help="Source of the PolitiFact article. "
                                                                  "Can be a URL, or '/path/to/csv/file:index' to "
                                                                  "specify a .csv file and the index row.")
    parser.add_argument("-m", "--meme_images", nargs='+', required=False, help="List of source meme images. "
                                                                               "Can be an ImgFlip ID, ImgFlip name or ImgFlip URL."
                                                                               " Check https://imgflip.com/memetemplates for options."
                                                                               " If you plan to run the baseline variant a meme image"
                                                                               " must be given. Separate multiple entries with spaces.")
    parser.add_argument('--variant', choices=['baseline', 'rag', 'debate, rlhf'], required=True,
                        help="Select the project variant to run. If you plan to run the baseline variant "
                             "the meme image must be given.")
    parser.add_argument('--config', default='config.yaml', required=True, help="Path to the configuration file")
    parser.add_argument('--moderate', action='store_true', help="Enable content moderation")
    parser.add_argument('--ablation', default='default', help="Check the config.yaml file for all the possible "
                                                              "input combinations to test the system with.")
    parser.add_argument('--bot', action='store_true', help="Enable X bot")

    return parser.parse_args()


def run_meme_fact(settings=None) -> List[Meme]:
    if not settings:
        settings = parse_arguments()
        settings = vars(settings)
        print(settings)
    runner = MemeFactRunner(settings['config'])
    try:
        return runner.run(settings)
    except Exception as e:
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()
        print("Shutting down MemeFact...")


if __name__ == "__main__":
    run_meme_fact()
