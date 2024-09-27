import logging
from typing import List
from modules.module1_input import AblationInput
from data.schemas import Meme
from modules.module2_selection import SelectionModule
from models.model_wrapper import ModelWrapper
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenerationModule(ABC):

    def __init__(self, ablation_input: AblationInput):
        self.input = ablation_input

    @abstractmethod
    def generate_captions(self, num_memes: int) -> List[Meme]:
        pass


class BaselineGenerationModule(GenerationModule):
    def __init__(self, ablation_input: AblationInput):
        super().__init__(ablation_input)
        logger.info("BaselineGenerationModule initialized")

    def generate_captions(self, num_memes: int) -> List[Meme]:
        lc = ModelWrapper()
        model = lc.get_gpt4o()

        memes = []
        claim = self.input.get_claim()
        verdict = self.input.get_verdict()
        iytis = self.input.get_iytis(),
        meme_image = self.input.get_meme_image()
        meme_image_url = meme_image.get_url()
        meme_image_box_count = meme_image.get_box_count()

        for _ in range(num_memes):
            meme_captions = lc.send_message(model=model,
                                            claim=claim,
                                            verdict=verdict,
                                            iytis=iytis,
                                            meme_image_url=meme_image_url,
                                            box_count=meme_image_box_count)

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
