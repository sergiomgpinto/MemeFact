import pandas as pd
import yaml
import json
import time
from dotenv import load_dotenv
from tqdm import tqdm
from models.model import ModelParameters
from models.model_manager import ModelManager
from utils.helpers import load_config
import logging
from datetime import datetime
from pathlib import Path
from utils.helpers import get_git_root


def _is_own_meme(model_name: str, meme_number: int) -> bool:
    model_meme_mapping = {
        'claude-3.5-sonnet': 1,
        'gemini-1.5-pro': 2,
        'gpt-4o': 3,
        'llama-3.2-90b-vision-instruct': 4,
        'pixtral-large-2411': 5,
        'qwen-2-vl-72b-instruct': 6,
        'qwq-32b-preview': 7
    }
    return model_meme_mapping.get(model_name) == meme_number


def setup_logging():
    rep_root_dir = get_git_root()
    log_dir = Path(rep_root_dir) / 'llm_judge' / 'data' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    log_file = log_dir / f'xbot_{timestamp}.log'

    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )
    logging.info(f"Log file created at: {log_file}")


def get_logger(name):
    return logging.getLogger(name)


def log_print(*args, **kwargs):
    message = ' '.join(map(str, args))
    logging.info(message)
    #print(message, **kwargs)


class LLMEvalStudy:
    def __init__(self):
        load_dotenv()
        settings = load_config('llm_judge_study.yaml')
        self.models = settings['models']
        self.evals = {}
        self.claims = pd.read_csv(get_git_root() / 'llm_judge' / 'data' / 'claims.csv')
        self.results = []
        self.model_manager = ModelManager(ModelParameters(max_tokens=1024), False)
        self.examples_ratings = pd.read_csv(get_git_root() / 'llm_judge' / 'data' / 'examples_ratings.csv')
        self.meme_urls = self.load_meme_urls()

    def load_meme_urls(self):
        cache_path = get_git_root() / 'llm_judge' / 'data' / 'meme_urls.json'
        if cache_path.exists():
            with open(cache_path, "r") as file:
                return json.load(file)
        return {}

    def format_meme_examples(self, examples_df):
        """Formats meme examples with their scores and URLs."""
        formatted_examples = []

        for _, row in examples_df.iterrows():
            formatted_examples.append(
                f"- Meme URL: {self.meme_urls[str(row['claim_number'])][str(row['meme_number'])]}\n"
                f"  - Coherence: {row['coherence']}/5\n"
                f"  - Clarity: {row['clarity']}/5\n"
                f"  - Hilarity: {row['hilarity']}/5\n"
                f"  - Persuasiveness: {row['persuasiveness']}/5\n"
                f"  - Template Appropriateness: {row['template_appropriateness']}/5"
            )

        return "\n\n".join(formatted_examples)

    def evaluate_meme(self, model, claim_number: int, meme_number: int, mode: str):
        claim_text = self.claims[self.claims['claim_number'] == claim_number]['claim_text'].iloc[0]
        claim_str = str(claim_number)
        meme_str = str(meme_number)

        if claim_str in self.meme_urls and meme_str in self.meme_urls[claim_str]:
            meme_main_url = self.meme_urls[claim_str][meme_str]
        else:
            print(f"Warning: Meme {meme_str} not found in Claim {claim_number}.")
            log_print(f"Warning: Meme {meme_str} not found in Claim {claim_number}.")
            return None

        # Select worst and best examples, excluding the meme being evaluated
        worst_examples = self.examples_ratings[
            (self.examples_ratings['claim_number'] == claim_number) &
            (self.examples_ratings['evaluation_type'] == 'worst') &
            (self.examples_ratings['meme_number'] != meme_number)
            ].head(2)

        best_examples = self.examples_ratings[
            (self.examples_ratings['claim_number'] == claim_number) &
            (self.examples_ratings['evaluation_type'] == 'best') &
            (self.examples_ratings['meme_number'] != meme_number)
            ].head(2)

        # Get the URLs of the bad and good memes
        bad_memes_urls = [self.meme_urls[str(row['claim_number'])][str(row['meme_number'])] for _, row in
                          worst_examples.iterrows()]
        good_memes_urls = [self.meme_urls[str(row['claim_number'])][str(row['meme_number'])] for _, row in
                           best_examples.iterrows()]

        # Format the bad and good meme examples as strings with ratings
        bad_memes = self.format_meme_examples(worst_examples)
        good_memes = self.format_meme_examples(best_examples)

        print(f"Processing Claim {claim_number}, Meme {meme_number} - {meme_main_url}")
        log_print(f"Processing Claim {claim_number}, Meme {meme_number} - {meme_main_url}")
        print(f'Prompting {model} in mode {mode}.')
        log_print(f'Prompting {model} in mode {mode}.')

        # Prepare parameters for the model
        prompt_params = {
            'claim_text': claim_text,
            'bad_memes': bad_memes,
            'good_memes': good_memes,
            'meme_main_url': meme_main_url,
            'bad_memes_urls': bad_memes_urls,
            'good_memes_urls': good_memes_urls,
            'meme_image': {
                'url': [
                    meme_main_url,  # Meme being evaluated
                    *bad_memes_urls,  # Two bad examples
                    *good_memes_urls  # Two good examples
                ]
            }
        }
        max_retries = 5
        retries = 0

        while retries < max_retries:
            try:
                if model == "gpt-4o":
                    response, confidence = self.model_manager.inference_model(model, 'llm-judge-study', prompt_params,
                                                                              mode=mode)
                else:
                    response = self.model_manager.inference_model(model, 'llm-judge-study', prompt_params, mode=mode)
                    confidence = None

                # Attempt YAML parsing
                parsed_response = yaml.safe_load(response)

                # Ensure the parsed response has the expected structure
                if 'output' in parsed_response and 'scores' in parsed_response['output']:
                    #print(parsed_response['output']['explanation'])
                    #print(parsed_response['output']['meme_description'])
                    #print(parsed_response['output']['meme_url'])
                    #print(parsed_response['output']['input_support'])
                    return parsed_response['output'], confidence, prompt_params

                print(f"Warning: Invalid response format received from {model}. Retrying...")
                log_print(f"Warning: Invalid response format received from {model}. Retrying...")

            except yaml.YAMLError as e:
                print(f"Error parsing YAML response for claim {claim_number}, meme {meme_number}: {e}")
                log_print(f"Error parsing YAML response for claim {claim_number}, meme {meme_number}: {e}")
            except Exception as e:
                print(f"Unexpected error in model response for claim {claim_number}, meme {meme_number}: {e}")
                log_print(f"Unexpected error in model response for claim {claim_number}, meme {meme_number}: {e}")

            retries += 1
            time.sleep(1)

        print(f"Error: Max retries reached for claim {claim_number}, meme {meme_number}. Returning None.")
        log_print(f"Error: Max retries reached for claim {claim_number}, meme {meme_number}. Returning None.")
        return None, None, None

    def run(self, save_interval=10, repetitions=20):
        save_counter = 0
        for model_name in tqdm(self.models, desc="Models"):
            for claim_number in tqdm(range(1, 13), desc="Claims"):
                for meme_number in range(1, 9):
                    for i in range(repetitions):
                        mode = "deterministic" if i < 10 else "creative"

                        try:
                            result, real_confidence, prompt_params = self.evaluate_meme(model_name, claim_number, meme_number, mode)

                            if result:
                                # Store successful evaluation
                                self.results.append({
                                    'model_name_judge': model_name,
                                    'claim_number': claim_number,
                                    'meme_number': meme_number,
                                    'evaluation_mode': mode,
                                    'repetition_number': i + 1 % 5,
                                    'real_meme_url': prompt_params['meme_main_url'],
                                    'bad_example_memes': prompt_params['bad_memes_urls'],
                                    'good_example_memes': prompt_params['good_memes_urls'],
                                    'self_reported_meme_url': result['meme_url'],
                                    'meme_description': result['meme_description'],
                                    'coherence': result['scores']['coherence'],
                                    'clarity': result['scores']['clarity'],
                                    'hilarity': result['scores']['hilarity'],
                                    'persuasiveness': result['scores']['persuasiveness'],
                                    'template_appropriateness': result['scores']['template_appropriateness'],
                                    'self_reported_confidence': result['confidence'],
                                    'explanation': result['explanation'],
                                    'is_own_meme': _is_own_meme(model_name, meme_number),
                                    'real_confidence': real_confidence,
                                    'error': False
                                })
                            else:
                                log_print("Received empty result from evaluation.")
                                raise ValueError("Received empty result from evaluation.")

                        except Exception as e:
                            print(f"Error processing claim {claim_number}, meme {meme_number}, model {model_name}, repetition {save_counter % save_interval}, mode {mode}: {e}")
                            log_print(f"Error processing claim {claim_number}, meme {meme_number}, model {model_name}, repetition {save_counter % save_interval}, mode {mode}: {e}")
                            self.results.append({
                                'model_name_judge': model_name,
                                'claim_number': claim_number,
                                'meme_number': meme_number,
                                'evaluation_mode': mode,
                                'repetition_number': i + 1 % 5,
                                'real_meme_url': None,
                                'bad_example_memes': None,
                                'good_example_memes': None,
                                'self_reported_meme_url': None,
                                'meme_description': None,
                                'coherence': None,
                                'clarity': None,
                                'hilarity': None,
                                'persuasiveness': None,
                                'template_appropriateness': None,
                                'self_reported_confidence': None,
                                'explanation': None,
                                'is_own_meme': None,
                                'real_confidence': None,
                                'error': True
                            })

                        save_counter += 1
                        print(f'Evaluation number {save_counter}. {6*12*8*repetitions - save_counter} left.')
                        log_print(f'Evaluation number {save_counter}. {6*12*8*repetitions - save_counter} left.')
                        if save_counter % save_interval == 0:
                            self._save_results(partial=True)

        self._save_results(partial=False)

    def _save_results(self, partial=False):
        results_df = pd.DataFrame(self.results)
        timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        results_dir = get_git_root() / 'llm_judge' / 'plots'

        if partial:
            output_path = results_dir / "partial_results.csv"
            print(f"Saving partial plots to {output_path}")
            log_print(f"Saving partial plots to {output_path}")
        else:
            output_path = results_dir / f"{timestamp}.csv"
            print(f"Saving final plots to {output_path}")
            log_print(f"Saving final plots to {output_path}")

        results_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    study = LLMEvalStudy()
    setup_logging()
    study.run()
