import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from data.schemas import InputData, MemeImage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AblationInput:
    rationale: Optional[str] = None
    claim: Optional[str] = None
    verdict: Optional[str] = None
    iytis: Optional[str] = None
    title: Optional[str] = None
    fact_checker: Optional[str] = None
    meme_images: Optional[List[MemeImage]] = field(default_factory=list)

    def get_claim(self):
        return self.claim

    def get_verdict(self):
        return self.verdict

    def get_rationale(self):
        return self.rationale

    def get_iytis(self):
        return self.iytis

    def get_meme_images(self):
        return self.meme_images

    def to_dict(self) -> dict:
        result = {k: v for k, v in self.__dict__.items() if v is not None}
        if 'meme_images' in result:
            result['meme_images'] = [meme_image.to_dict() for meme_image in result['meme_images']]
        return result


class InputModule:
    def __init__(self, input_data: InputData, ablation_mode: str, ablation_dict: Dict):
        self.input = input_data
        self.ablation_input = self._parse_ablation_input(ablation_mode, ablation_dict)
        logger.info("InputModule initialized")

    def get_input(self) -> InputData:
        return self.input

    def non_meme_image_input_mode(self) -> bool:
        return not self.input.get_meme_images()

    def get_ablation_input(self):
        return self.ablation_input

    def _parse_ablation_input(self, ablation_mode: str, ablation_dict: Dict):

        article = self.input.get_article()
        meme_images = self.input.get_meme_images()

        possible_inputs = {'meme_images': meme_images, **article.to_dict()}

        for key, value in ablation_dict['combinations'].items():
            if key == ablation_mode:
                filtered_inputs = {k: v for k, v in possible_inputs.items() if k in value}
                filtered_inputs['fact_checker'] = article.__class__.__name__[:-7].lower()
                return AblationInput(**filtered_inputs)
        raise ValueError('Wrong ablation mode. Check the config.yaml for the possible combinations.')
