#import torch
from abc import ABC, abstractmethod
from models.prompt import Prompt
#from transformers import AutoModel, AutoTokenizer, AutoProcessor


class BaseModel(ABC):

    @abstractmethod
    def prompt(self, prompt: Prompt):
        pass

    def _parse_response(self, response):
        pass


class ProprietaryModel(BaseModel, ABC):

    def __init__(self, client):
        self.client = client


class OpenSourceModel(BaseModel, ABC):
    def __init__(self, model_name):
        pass
        #self.model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        #self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        #self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        #self.device = "cuda" if torch.cuda.is_available() else "cpu"

    @abstractmethod
    def _encode_input(self, text: str, image):
        pass

    @abstractmethod
    def _decode_output(self, output):
        pass
