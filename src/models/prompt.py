import re
from abc import ABC, abstractmethod
from typing import Dict
from utils.helpers import load_config


class PromptManager:

    def __init__(self, model, model_name):
        self.model = model
        self.prompt_config = load_config('prompts.yaml')
        self.promptTypes = {
            'zero-shot': lambda prompt_params: ZeroShotPrompt(self.prompt_config, prompt_params, model_name),
            'few-shot': lambda prompt_params: FewShotPrompt(self.prompt_config, prompt_params),
            'cot-prompt': lambda prompt_params: CoTPrompt(self.prompt_config, prompt_params),
        }

    def generate_prompt(self, prompt_type, prompt_params):
        return self.model.prompt(self.promptTypes[prompt_type](prompt_params))


class Prompt(ABC):

    def __init__(self, config: Dict, params: Dict, model: str):
        self.class_name = re.sub(r'(?<!^)(?=[A-Z])', '-',
                                 self.__class__.__name__.split('Prompt')[0]).lower()
        self.text, self.image = self._parse_prompt(config, params, model)

    def get_text(self):
        return self.text

    def get_image(self):
        return self.image

    @abstractmethod
    def _parse_prompt(self, config: Dict, params: Dict, model: str):
        pass


class ZeroShotPrompt(Prompt):

    def __init__(self, config: Dict, params: Dict, model: str):
        super().__init__(config, params, model)

    def _parse_prompt(self, config: Dict, params: Dict, model: str):
        text = config[self.class_name]['template'].format(**params)
        if not params['meme_image']:
            return text, None
        if model == 'gpt-4o' or model == 'claude-3.5-sonnet':
            return text, str(params['meme_image']['url'])
        elif model == 'gemini-1.5-pro':
            meme_image_name = params['meme_image']['name']
            return text, meme_image_name
        else:
            print("code not done")
            return None, None


class FewShotPrompt(Prompt):

    def __init__(self, config: Dict, params: Dict):
        super().__init__(config, params)


class CoTPrompt(Prompt):

    def __init__(self, config: Dict, params: Dict):
        super().__init__(config, params)
