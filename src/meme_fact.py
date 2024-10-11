from abc import ABC, abstractmethod
from data.schemas import Meme
from typing import List
from modules.module1_input import InputModule
from modules.module3_generation import GenerationModule
from modules.module4_concatenation import ConcatenationModule
from modules.module5_moderation import ModerationModule
from utils.helpers import download_memes
from utils.input_parser import InputParser


class MemeFact(ABC):

    def __init__(self, config):
        self.config = config
        self.class_name = f'{self.__class__.__name__.split('Variant')[0]}'.lower()
        self.filtered_memes = None

    def run(self, args) -> List[Meme]:
        parser = InputParser(args)
        input_data = parser.parse()
        input_module = InputModule(input_data=input_data,
                                   ablation_mode=args['ablation'],
                                   ablation_dict=self.config['ablation'])
        print(f'Running {self.__class__.__name__}.')

        self.filtered_memes = self._run_impl(input_module, **args)
        self._output_memes(args['bot'])
        return self.filtered_memes

    def _output_memes(self, bot_run: bool):
        download_memes(self.filtered_memes, bot_run)

    def _run_moderation_pipeline(self, generation_module: GenerationModule, num_memes: int,
                                 enable_moderation: bool, model: str, prompt_type: str) -> List[Meme]:
        moderation_pipeline = MemeModerationPipeline(generation_module=generation_module, enable_moderation=enable_moderation)
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
