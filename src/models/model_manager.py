from dotenv import load_dotenv
from models.open_source.models import PixTralLarge, LlamaVision, QwenVision, QwenPreview
from models.proprietary.models import Gpt4o, GeminiPro, ClaudeSonnet
from models.prompt import PromptManager


class ModelManager:
    def __init__(self, params, parse):
        load_dotenv()
        self.models = {
            'gpt-4o': Gpt4o(params, parse),
            'gemini-1.5-pro': GeminiPro(params, parse),
            'claude-3.5-sonnet': ClaudeSonnet(params, parse),
            'pixtral-large-2411': PixTralLarge(params),
            'llama-3.2-90b-vision-instruct': LlamaVision(params),
            'qwen-2-vl-72b-instruct': QwenVision(params),
            "qwq-32b-preview": QwenPreview(params)
        }

    def inference_model(self, model: str, prompt_type: str, prompt_params, **params):
        promptManager = PromptManager(self.models[model], model)
        return promptManager.generate_prompt(prompt_type, prompt_params, **params)
