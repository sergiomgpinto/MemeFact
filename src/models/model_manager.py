from typing import Dict
from dotenv import load_dotenv
from models.proprietary.models import Gpt4o, GeminiPro, ClaudeSonnet
from models.prompt import PromptManager


class ModelManager:
    def __init__(self):
        load_dotenv()
        self.models = {
            'gpt-4o': Gpt4o(),
            'gemini-1.5-pro': GeminiPro(),
            'claude-3.5-sonnet': ClaudeSonnet(),
            #'intern-vl2': InternVL2(),
        }

    def inference_model(self, model: str, prompt_type: str, prompt_params: Dict):
        promptManager = PromptManager(self.models[model], model)
        return promptManager.generate_prompt(prompt_type, prompt_params)

