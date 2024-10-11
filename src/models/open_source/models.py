import torch
from PIL.Image import Image
from models.model import OpenSourceModel
from models.prompt import Prompt


class InternVL2(OpenSourceModel):

    def __init__(self):
        model_name = "OpenGVLab/InternVL2-Llama3-76B"
        super().__init__(model_name)

    def prompt(self, prompt: Prompt):
        try:
            inputs = self._encode_input(prompt.get_text(), None)
            with torch.no_grad():
                output = self.model.generate(**inputs)
            return self._decode_output(output)
        except Exception as e:
            print(f"Error in InternVL2Model prompt: {e}")
            return ""

    def _encode_input(self, text: str, image):
        text_input = self.tokenizer(text, return_tensors="pt").to(self.device)

        if image is not None:
            if isinstance(image, str):
                image = Image.open(image).convert("RGB")
            image_input = self.processor(images=image, return_tensors="pt").to(self.device)
            inputs = {**text_input, **image_input}
        else:
            inputs = text_input
        return inputs

    def _decode_input(self, output):
        decoded_output = self.tokenizer.decode(output, skip_special_tokens=True)
        print(decoded_output)
        return decoded_output
