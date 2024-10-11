import logging
from typing import List
from models.model_manager import ModelManager
from modules.module1_input import AblationInput
from data.schemas import Meme
from modules.module2_selection import SelectionModule
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenerationModule(ABC):

    def __init__(self, ablation_input: AblationInput):
        self.input = ablation_input
        self.model_manager = ModelManager()

    @abstractmethod
    def generate_captions(self, num_memes: int, model: str, prompt_type: str) -> List[Meme]:
        pass


class BaselineGenerationModule(GenerationModule):
    def __init__(self, ablation_input: AblationInput):
        super().__init__(ablation_input)
        logger.info("BaselineGenerationModule initialized")

    def generate_captions(self, num_memes: int, model: str, prompt_type: str) -> List[Meme]:
        memes = []
        meme_images = self.input.get_meme_images()
        prompt_params = self.input.to_dict()
        for index, meme_image in enumerate(meme_images):
            current_params = prompt_params.copy()
            current_params['meme_image'] = current_params['meme_images'][index]
            del current_params['meme_images']
            meme_captions = self.model_manager.inference_model(model, prompt_type, current_params)

            if not meme_captions:
                print(f'Failed attempt to generate captions for {meme_image}.')
                continue
            meme = Meme(meme_image=meme_image,
                        captions=meme_captions)
            memes.append(meme)
        return memes


class RAGGenerationModule(GenerationModule):
    def __init__(self, ablation_input: AblationInput, selection_module: SelectionModule):
        super().__init__(ablation_input)
        self.selection_module = selection_module
        logger.info("RagGenerationModule initialized")

    def generate_captions(self, num_memes: int) -> List[Meme]:
        retrieved_data = self.selection_module.rag()
        print("CODE IS NOT DONE")
        memes = []
        return memes


class DebateGenerationModule(GenerationModule):
    def __init__(self, ablation_input: AblationInput, selection_module: SelectionModule):
        super().__init__(ablation_input)
        self.selection_module = selection_module
        logger.info("DebateGenerationModule initialized")

    def generate_captions(self, num_memes: int) -> List[Meme]:
        retrieved_data = self.selection_module.rag()
        print("CODE IS NOT DONE")
        memes = []
        return memes
