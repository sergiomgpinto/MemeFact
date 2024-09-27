import itertools
import traceback

import pandas as pd
from typing import Dict, List
from src.run_meme_fact import run_meme_fact


def _generate_experiment_combinations(experiment_params: Dict[str, List]) -> List[Dict]:
    keys, values = zip(*experiment_params.items())
    return [dict(zip(keys, v)) for v in itertools.product(*values)]


def run_baseline(args):
    run_meme_fact(args)


def run_ablation(args):
    experiment_params = {'ablation': ["C+V+R", "C+V+IYTIS", "C+V+R+IYTIS", "MI+C+V+R", "default", "MI+C+V+R+IYTIS"]}

    combinations = _generate_experiment_combinations(experiment_params)

    for i, params in enumerate(combinations, 1):
        print(f"\nRunning experiment {i}/{len(combinations)}:")
        print(params)

        try:
            experiment_args = {**args, **params}
            print(experiment_args)
            run_meme_fact(experiment_args)
        except Exception as e:
            print(f"Error in experiment {i}: {str(e)}")
            traceback.print_exc()


def run_meme_image_for_all_article(args):
    file_path = 'data/raw/politifact_us_presi_elections2024_20240917_173046.csv'
    file = pd.read_csv(file_path)

    for index, row in file.iterrows():
        experiment_args = args.copy()
        experiment_args['politifact'] = f"{file_path}:{index}"

        try:
            print(f"Running experiment for row {index}:")
            print(experiment_args)
            run_meme_fact(experiment_args)
        except Exception as e:
            print(f"Error in row {index}: {str(e)}")
            # traceback.print_exc()
        print("\n" + "-" * 50 + "\n")


def run_article_for_all_meme_image(args):
    file_path = 'data/raw/meme_images_20240920_124503.csv'
    file = pd.read_csv(file_path)

    for index, row in file.iterrows():
        experiment_args = args.copy()
        experiment_args['meme_image'] = row.get('name')

        try:
            print(f"Running experiment for row {index}:")
            print(experiment_args)
            run_meme_fact(experiment_args)
        except Exception as e:
            print(f"Error in row {index}: {str(e)}")
            # traceback.print_exc()
        print("\n" + "-" * 50 + "\n")
        break


def run_meme_fact_n_times(args, n):
    for i in range(n):
        print(f"\nRun number {i}")
        try:
            run_meme_fact(args)
        except Exception as e:
            print(f"Error in experiment {i}: {str(e)}")


if __name__ == '__main__':
    args = {'politifact': 'https://www.politifact.com/factchecks/2024/sep/25/tim-walz/fact-checking-tim-walz-on-which-president-added-th/','meme_image': 'https://i.imgflip.com/30b1gx.jpg','variant': 'baseline', 'config': 'config.yaml', 'moderate': False, 'ablation': 'default'}
    run_baseline(args)
    # run_ablation(args)
    ########################################
    #args = {'memeimage': 'https://i.imgflip.com/30b1gx.jpg', 'variant': 'baseline', 'config': 'config.yaml', 'moderate': False, 'ablation': 'default'}
    #run_meme_image_for_all_article(args)
    # args = {'memeimage': 'https://i.imgflip.com/30b1gx.jpg', 'variant': 'baseline', 'config': 'config.yaml', 'moderate': False, 'ablation': 'default'}
    #args = {'politifact': 'https://www.politifact.com/factchecks/2024/sep/25/tim-walz/fact-checking-tim-walz-on-which-president-added-th/', 'variant': 'baseline', 'config': 'config.yaml', 'moderate': False, 'ablation': 'default'}
    #run_article_for_all_meme_image(args)
    #args = {'politifact': 'https://www.politifact.com/factchecks/2024/sep/25/tim-walz/fact-checking-tim-walz-on-which-president-added-th/', 'variant': 'baseline', 'config': 'config.yaml', 'moderate': False, 'ablation': 'default', 'meme_image': 'Drake Hotline Bling'}
    #run_meme_fact_n_times(args, 50)
