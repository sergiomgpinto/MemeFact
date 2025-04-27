from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from utils.helpers import get_git_root, load_config


class HatefulMemeDetectionModel:
    def __init__(self):
        self.config = load_config("config.yaml")
        model = self.config["moderation"]["hmd"]

        if model == 'openai/clip-vit-base-patch32':
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        self.model = CLIPModel.from_pretrained(model)
        self.threshold = self.config["moderation"]["threshold"]

    def detect(self, image_path):
        image = Image.open(image_path)
        inputs = self.processor(
            text=["hateful content", "non hateful content"],
            images=image,
            return_tensors="pt",
            padding=True
        )
        outputs = self.model(**inputs)
        logits = outputs.logits_per_image
        probs = logits.softmax(dim=1)

        return bool(probs[0][0] > self.threshold)


if __name__ == "__main__":
    detector = HatefulMemeDetectionModel()
    root_path = get_git_root()
    meme_path = root_path / 'output' / '10_memes_2024_12_02_13_49_12' / '1_Hard To Swallow Pills.png'
    print(detector.detect(meme_path))
