import pandas as pd
from rag.knowledge_graph import load_config
from run_meme_fact import run_meme_fact
from utils.helpers import get_git_root


class MemesGenerator:
    def __init__(self):
        filename = 'misc/meta_study_evidence.jsonl'
        self.df = pd.read_json(filename, lines=True)
        self.config = load_config('meta_study.yaml')
        self.meme_fact_config = {'config': 'config.yaml', 'variant': self.config['variant'],
                                 'moderate': self.config['moderate'],
                                 'ablation': self.config['ablation'],
                                 'bot': True,
                                 'num_memes': self.config['num_memes'],
                                 'model': 'claude-3.5-sonnet'}

    def run(self):
        path = get_git_root() / 'meta_study' / 'meta_study_evidence_human_summaries.jsonl'
        for index, row in self.df.iterrows():

            running_config = {'article': f'{path}:{index}', 'meme_images': [], **self.meme_fact_config}
            memes = run_meme_fact(settings=running_config)

            if len(memes) == 0:
                print(f'MemeFact did not generate one meme.')
                print("Finished action cycle unsuccessfully.")
                return


if __name__ == '__main__':
    runner = MemesGenerator()
    runner.run()