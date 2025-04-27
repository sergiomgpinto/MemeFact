import logging
from typing import List
from models.model_manager import ModelManager
from modules.debate_manager import DebateManager
from modules.module1_input import AblationInput
from data.schemas import Meme
from modules.module2_selection import SelectionModule
from abc import ABC, abstractmethod
from utils.img_flip_api import ImgFlipAPI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenerationModule(ABC):

    def __init__(self, ablation_input: AblationInput, params, parse):
        self.input = ablation_input
        self.model_manager = ModelManager(params, parse)
        self.img_flip_api = ImgFlipAPI()

    @abstractmethod
    def generate_captions(self, num_memes: int, model: str, prompt_type: str) -> List[Meme]:
        pass

    def _prepare_generation_params(self, retrieved_data: list, index: int, params: dict) -> tuple:
        if len(self.input.get_meme_images()) == 1:
            data = retrieved_data[0]
            current_image = self.input.get_meme_images()[0]
        else:
            data = retrieved_data[index]
            current_image = self.img_flip_api.get_meme_image(data['id']).get_data()

        params['meme_image'] = current_image.to_dict()
        params['meme_image_description'] = data['description']
        params['meme_image_instances'] = data['captions']
        params['meme_image_caption_style'] = data['caption_style_explanation']
        params['box_count'] = data['box_count']
        params['meme_template_name'] = data['template_title']

        if 'about' in data:
            params['kym_about'] = data['about']

        return params, current_image


class BaselineGenerationModule(GenerationModule):
    def __init__(self, ablation_input: AblationInput, params, parse):
        super().__init__(ablation_input, params, parse)
        logger.info("BaselineGenerationModule initialized")

    def generate_captions(self, num_memes: int, model: str, prompt_type: str) -> List[Meme]:
        memes = []
        meme_images = self.input.get_meme_images()

        iterations = len(meme_images) if len(meme_images) > 1 else num_memes
        meme_image = meme_images[0] if len(meme_images) == 1 else None

        for index in range(iterations):
            current_image = meme_image or meme_images[index]
            params = self.input.to_dict()
            params['meme_image'] = current_image.to_dict()

            meme_captions = self.model_manager.inference_model(model, prompt_type, params)

            if not meme_captions:
                print(f'Failed attempt to generate captions for {current_image}.')
                continue

            memes.append(Meme(
                meme_image=current_image,
                captions=meme_captions
            ))

        return memes


class RAGGenerationModule(GenerationModule):
    def __init__(self, ablation_input: AblationInput, selection_module: SelectionModule, params, parse):
        super().__init__(ablation_input, params, parse)
        self.selection_module = selection_module
        logger.info("RagGenerationModule initialized")

    def generate_captions(self, num_memes: int, model: str, prompt_type: str) -> List[Meme]:
        memes = []
        retrieved_data = self.selection_module.rag(num_memes=num_memes)
        if not retrieved_data:
            logger.error("RAG could not retrieve data.")
            return memes

        for index in range(num_memes):
            iteration_params = self.input.to_dict().copy()
            iteration_params, current_image = self._prepare_generation_params(retrieved_data, index, iteration_params)
            meme_captions = self.model_manager.inference_model(model, prompt_type, iteration_params)

            if not meme_captions:
                print(f'Failed attempt to generate captions for {current_image}.')
                continue

            memes.append(Meme(
                meme_image=current_image,
                captions=meme_captions
            ))
        return memes


class DebateGenerationModule(GenerationModule):
    def __init__(self, ablation_input: AblationInput, selection_module: SelectionModule, generators, evaluators, params, parse):
        super().__init__(ablation_input, params, parse)
        self.selection_module = selection_module
        self.generators = generators
        self.evaluators = evaluators
        self.debate_manager = DebateManager(generators=generators, evaluators=evaluators, model_manager=self.model_manager)
        logger.info("DebateGenerationModule initialized")

    def generate_captions(self, num_memes: int, model: str, prompt_type: str) -> List[Meme]:
        memes = []
        retrieved_data = self.selection_module.rag(num_memes=num_memes)
        if not retrieved_data:
            logger.error("RAG could not retrieve data.")
            return memes

        for index in range(num_memes):
            iteration_params = self.input.to_dict().copy()
            iteration_params, current_image = self._prepare_generation_params(retrieved_data, index, iteration_params)
            meme_captions = self.debate_manager.run_debate(iteration_params)

            if not meme_captions:
                print(f'Failed attempt to generate captions for {current_image}.')
                continue

            memes.append(Meme(
                meme_image=current_image,
                captions=meme_captions
            ))
        return memes
