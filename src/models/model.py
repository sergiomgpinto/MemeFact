import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from models.prompt import Prompt


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_content_prefix(content):
    refusal_indicators = [
        "I'm sorry, but I can't",
        "I don't have information about",
        "I'm not able to",
        "I cannot provide",
        "I'm not comfortable",
        "I don't have access to",
        "I'm not authorized to",
    ]

    if any(indicator.lower() in content.lower() for indicator in refusal_indicators):
        raise Exception("The model refused to generate content.")

    contents = []
    lines = content.split('\n')
    print("*****GENERATED OUTPUT*****")
    for line in lines:
        if (line.startswith('Caption') or line.startswith('Question') or
                line.startswith('Answer')):
            print(f'CONTENT LINE: {line}')
            content = line.split(':', 1)[1].strip()
            content = content.replace('"', '')
            contents.append(content)
        elif line.startswith('Reasoning'):
            print(f'CONTENT LINE: {line}')
            reasoning = line.split(':', 1)[1].strip()
            reasoning = reasoning.replace('"', '')
            contents.append(f'Reasoning: {reasoning}')
        else:
            print(f"OTHER LINE: {line}")
    print("*****END GENERATED OUTPUT*****")
    return contents


@dataclass
class ModelParameters:
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    seed: Optional[int] = None

    def __post_init__(self):
        if self.temperature is None:
            self.temperature = 1.0

    def to_dict(self, model_name: str):
        if model_name == 'gpt-4o':
            return {k: v for k, v in self.__dict__.items() if v is not None and v != -1 and k != 'top_k'}
        elif model_name == 'gemini-1.5-pro':
            return {k if k != 'max_tokens' else 'max_output_tokens': v for k, v in self.__dict__.items() if v is not None and v != -1 and k != 'seed'}
        elif model_name == 'claude-3.5-sonnet':
            return {k: v for k, v in self.__dict__.items() if v is not None and v != -1 and k != 'seed'}
        return {k: v for k, v in self.__dict__.items() if v is not None and v != -1}


class BaseModel(ABC):

    @abstractmethod
    def prompt(self, prompt: Prompt, **params):
        pass

    @abstractmethod
    def _parse_response(self, response):
        pass
