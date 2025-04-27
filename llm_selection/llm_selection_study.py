import re
from datetime import datetime
from pathlib import Path
from run_meme_fact import run_meme_fact
from utils.helpers import load_config, get_git_root, download_image
from tqdm import tqdm


class LLMSelectionStudy:
    def __init__(self):
        settings = load_config('llm_selection_study.yaml')
        self.settings = {'config': 'llm_selection_study.yaml',
                         'variant': settings['variant'],
                         'moderate': settings['moderate'],
                         'ablation': 'default',
                         'manual_save': True,
                         'meme_images': settings['meme_images'],
                         'bot': False,
                         'num_memes': settings[settings['variant']]['num_memes']}
        self.articles = settings['articles']
        self.models = settings['models']
        self.memes = {}

    def _save_memes(self):
        root_dir = Path(get_git_root())
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        study_dir = root_dir / 'llm_selection' / timestamp

        study_dir.mkdir(parents=True, exist_ok=True)

        for article in self.memes:
            safe_article_name = re.sub(r'/', '_', article)
            article_dir = study_dir / safe_article_name
            article_dir.mkdir(parents=True, exist_ok=True)

            for model in self.memes[article]:
                model_dir = article_dir / model
                model_dir.mkdir(parents=True, exist_ok=True)
                for index, meme in enumerate(self.memes[article].get(model, []), start=1):
                    meme_filename = f'{index}_{meme.get_meme_image().get_name()}'
                    download_image(meme.get_url(), meme_filename, model_dir)

    def run(self):
        for article in tqdm(self.articles, desc='Generating memes', colour='green'):
            self.memes[article] = {}
            print(f'GENERATING MEMES FOR {article}')
            for model in self.models:
                print(f"RUNNING MODEL {model} ON ARTICLE {article}")
                run_settings = {'article': article, 'model': model, **self.settings}
                memes = run_meme_fact(settings=run_settings)
                if memes:
                    self.memes[article][model] = memes
                else:
                    self.memes[article][model] = []
        self._save_memes()


if __name__ == "__main__":
    study = LLMSelectionStudy()
    study.run()
