import logging
import requests
import json
import os
from dotenv import load_dotenv
from typing_extensions import override

from models.model import ModelParameters, BaseModel
from models.prompt import Prompt
from abc import ABC
from models.proprietary.models import parse_content_prefix

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenSourceModel(BaseModel, ABC):
    def __init__(self, model_name, params: ModelParameters):
        self.model_name = model_name
        self.api = OpenRouterApi()
        self.params = params

    def prepare_params(self, model_name, **params):
        final_params = self.params.to_dict(model_name).copy()

        if 'mode' in params:
            mode = params.pop('mode')
            if mode == 'deterministic':
                params['temperature'] = 0.2
            elif mode == 'creative':
                params['temperature'] = 0.7
            else:
                raise ValueError("Mode must be either 'deterministic' or 'creative'")

        if model_name == 'gpt-4o':
            params['logprobs'] = True
            params['top_logprobs'] = 5

        final_params.update(params)
        print(f'API Call Params:{final_params}')
        return final_params

    def _parse_response(self, response):
        return parse_content_prefix(response.json()['choices'][0]['message']['content'].strip())


class OpenRouterApi:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPEN_ROUTER_API_KEY')
        self.app_name = os.getenv('OPEN_ROUTER_APP_NAME')

    def post(self, model, text, image, params):
        content = [{"type": "text", "text": text}]
        if image:
            if isinstance(image, list):
                for img_url in image:
                    content.append({"type": "image_url", "image_url": {"url": img_url}})
            elif isinstance(image, str):
                content.append({"type": "image_url", "image_url": {"url": image}})

        data = json.dumps({"model": model, "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
                           **params
                           })
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Title": f"{self.app_name}",
                },
                data=data
            )
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"Failed to post request to OpenRouter API: {e}")
            return None


class PixTralLarge(OpenSourceModel):
    def __init__(self, params):
        super().__init__("mistralai/pixtral-large-2411", params)

    @override
    def prompt(self, prompt: Prompt, **params):
        response = self.api.post(model=self.model_name, text=prompt.get_text(),
                                 image=prompt.get_image(),
                                 params=self.prepare_params(self.model_name, **params))
        #return self._parse_response(response)
        return response.json()['choices'][0]['message']['content'].strip()


class LlamaVision(OpenSourceModel):
    def __init__(self, params):
        super().__init__("meta-llama/llama-3.2-90b-vision-instruct", params)

    @override
    def prompt(self, prompt: Prompt, **params):
        response = self.api.post(model=self.model_name, text=prompt.get_text(),
                                 image=prompt.get_image(),
                                 params=self.prepare_params(self.model_name, **params))
        #return self._parse_response(response)
        return response.json()['choices'][0]['message']['content'].strip()


class QwenVision(OpenSourceModel):
    def __init__(self, params):
        super().__init__("qwen/qwen-2-vl-72b-instruct", params)

    @override
    def prompt(self, prompt: Prompt, **params):
        response = self.api.post(model=self.model_name, text=prompt.get_text(),
                                 image=prompt.get_image(),
                                 params=self.prepare_params(self.model_name, **params))
        #return self._parse_response(response)
        return response.json()['choices'][0]['message']['content'].strip()


class QwenPreview(OpenSourceModel):
    def __init__(self, params):
        super().__init__("qwen/qwq-32b-preview", params)

    @override
    def prompt(self, prompt: Prompt, **params):
        response = self.api.post(model=self.model_name, text=prompt.get_text(),
                                 image=prompt.get_image(),
                                 params=self.params)
        get_captions_prompt = f'''
        From the following text, extract ONLY the final complete pair of captions.

        Input text:
        {response.json()['choices'][0]['message']['content'].strip()}

        Rules:
        1. Find the last occurrence of "Caption 1:"
        2. Extract the caption text that follows all instances of "Caption X: " after it
        3. If one caption text is missing go back to a previous occurrence of "Caption 1:" to find another set
        3. Output each line as "Caption X: " where X is the number of the caption
        4. Preserve the caption text exactly as it appears after "Caption X: "
        5. Do not include any other text or explanations
        '''
        print("*" * 100)
        response = self.api.post(model='meta-llama/llama-3.3-70b-instruct', text=get_captions_prompt, image=None,
                                 params=self.params)
        return response.json()['choices'][0]['message']['content'].strip()
