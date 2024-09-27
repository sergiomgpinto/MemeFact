import argparse
import traceback
import yaml
from baseline import BaselineVariant
from rag import RagVariant
from debate import DebateVariant
from rlhf import RlhfVariant


class MemeFactRunner:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.variants = {
            'baseline': BaselineVariant(self.config),
            'rag': RagVariant(self.config),
            'debate': DebateVariant(self.config),
            'rlhf': RlhfVariant(self.config)
        }

    def _load_config(self, config_path: str):
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)

    def run(self, args):
        self.variants[args['variant']].run(args)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate a meme explanation for a PolitiFact article.")

    parser.add_argument("-p", "--politifact", help="Source of the PolitiFact article. "
                                                   "Can be a URL, or '/path/to/csv/file:index' to "
                                                   "specify a .csv file and the index row.")
    parser.add_argument("-m", "--memeimage", required=False, help="Source of the meme image. "
                                                                  "Can be an ImgFlip ID, ImgFlip name or ImgFlip URL."
                                                                  " Check https://imgflip.com/memetemplates for options."
                                                                  " If you plan to run the baseline variant a meme image"
                                                                  " must be given.")
    parser.add_argument('--variant', choices=['baseline', 'rag', 'debate, rlhf'], required=True,
                        help="Select the project variant to run. If you plan to run the baseline variant "
                             "the meme image must be given.")
    parser.add_argument('--config', default='config.yaml', required=True, help="Path to the configuration file")
    parser.add_argument('--moderate', action='store_true', help="Enable content moderation")
    parser.add_argument('--ablation', default='default', help="Check the config.yaml file for all the possible "
                                                              "input combinations to test the system with.")

    return parser.parse_args()


def run_meme_fact(settings=None):
    if not settings:
        settings = parse_arguments()
        settings = vars(settings)
    runner = MemeFactRunner(settings['config'])
    try:
        runner.run(settings)
    except Exception as e:
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()
        print("Shutting down MemeFact...")


if __name__ == "__main__":
    run_meme_fact()
