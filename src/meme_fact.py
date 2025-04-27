import logging
import os
import warnings
from abc import ABC, abstractmethod
from data.schemas import Meme
from typing import List

from models.model import ModelParameters
from modules.module1_input import InputModule
from modules.module3_generation import GenerationModule
from modules.module4_concatenation import ConcatenationModule
from modules.module5_moderation import ModerationModule
from utils.helpers import download_memes
from utils.input_parser import InputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore", category=FutureWarning, module="transformers.tokenization_utils_base")


class MemeFact(ABC):

    def __init__(self, config):
        self.config = config
        self.class_name = f'{self.__class__.__name__.split('Variant')[0]}'.lower()
        self.filtered_memes = None

    def run(self, args) -> List[Meme]:
        parser = InputParser(args)
        input_data = parser.parse()

        if self.config[self.class_name]['num_memes'] < 1:
            raise ValueError("Invalid input. num_memes must be greater than 0.")

        if args['model'] not in ['gpt-4o', 'gemini-1.5-pro', 'claude-3.5-sonnet',
                                 'pixtral-large-2411', 'llama-3.2-90b-vision-instruct',
                                 'qwen-2-vl-72b-instruct', 'qwq-32b-preview']:
            raise ValueError("Invalid input. model must be one of 'gpt-4o', 'gemini-1.5-pro', 'claude-3.5-sonnet', "
                             "'pixtral-large-2411', 'llama-3.2-90b-vision-instruct', 'qwen-2-vl-72b-instruct'.")

        if self.config[self.class_name]['prompt_type'] not in ['zero-shot', 'few-shot', 'cot', 'cov', 'clot']:
            raise ValueError("Invalid input. prompt_type must be one of 'zero-shot', 'few-shot', 'cot', 'cov', 'clot'.")

        if not args['meme_images']:
            size = 0
        else:
            size = len(args['meme_images'])

        if args['variant'] == 'baseline' and not ((size == 1 and self.config[self.class_name]['num_memes'] >= 1) or (
                size == self.config[self.class_name]['num_memes'])):
            raise ValueError("Invalid input. Either one meme image is given to generate num_memes same image memes "
                             "or num_memes meme images are given to generate one meme each.")

        if args['variant'] == 'baseline' and self.config[self.class_name]['prompt_type'] != 'zero-shot':
            raise ValueError("Invalid input. Baseline variant only supports zero-shot prompt type.")

        if args['variant'] == 'rag' and self.config[self.class_name]['prompt_type'] == 'zero-shot':
            raise ValueError("Invalid input. RAG variant does not support zero-shot prompt type.")
        if args['variant'] == 'rag' and not (size == 1 or size == 0):
            raise ValueError("Invalid input. RAG variant only supports either no meme image or one meme image.")

        if args['variant'] == 'debate' and self.config[self.class_name]['prompt_type'] == 'zero-shot':
            raise ValueError("Invalid input. Debate variant does not support zero-shot prompt type.")
        if args['variant'] == 'debate' and not (size == 1 or size == 0):
            raise ValueError("Invalid input. Debate variant only supports either no meme image or one meme image.")

        input_module = InputModule(input_data=input_data,
                                   ablation_mode=args['ablation'],
                                   ablation_dict=self.config['ablation'])
        print(f'Running {self.__class__.__name__}.')

        params = {
            **args,
            'model_params': ModelParameters(**self.config['model_params']),
            'parse': self.config[self.class_name].get('parse', 'False') == 'True'
        }

        if 'generators' in self.config[self.class_name]:
            params['generators'] = self.config[self.class_name]['generators']
        if 'evaluators' in self.config[self.class_name]:
            params['evaluators'] = self.config[self.class_name]['evaluators']

        self.filtered_memes = self._run_impl(input_module, **params)
        if 'manual_save' not in args:
            self._output_memes(args['bot'])
        return self.filtered_memes

    def _output_memes(self, bot_run: bool):
        download_memes(self.filtered_memes, bot_run)

    def _run_moderation_pipeline(self, generation_module: GenerationModule, num_memes: int,
                                 enable_moderation: bool, model: str, prompt_type: str) -> List[Meme]:
        moderation_pipeline = MemeModerationPipeline(generation_module=generation_module,
                                                     enable_moderation=enable_moderation)
        return moderation_pipeline.run(num_memes=num_memes, model=model, prompt_type=prompt_type)

    @abstractmethod
    def _run_impl(self, input_module: InputModule, **kwargs) -> List[Meme]:
        pass


class MemeModerationPipeline:
    def __init__(self, generation_module: GenerationModule, enable_moderation: bool):
        self.generation_module = generation_module
        self.concatenation_module = ConcatenationModule()
        self.moderation_module = ModerationModule(enable_moderation=enable_moderation)

    def _verify_memes(self, filtered_memes: List[Meme]) -> bool:
        for meme in filtered_memes:
            if meme.is_hateful():
                logger.info(f"Meme {meme.get_url()} was considered hateful.")
                return False
        return True

    def run(self, num_memes: int, model: str, prompt_type: str) -> List[Meme]:
        while True:
            non_captioned_memes = self.generation_module.generate_captions(num_memes, model, prompt_type)
            meme_candidates = self.concatenation_module.generate_memes(non_captioned_memes)
            filtered_memes = self.moderation_module.moderate_memes(meme_candidates)
            safe_flag = self._verify_memes(filtered_memes)

            if safe_flag:
                break
        return filtered_memes
