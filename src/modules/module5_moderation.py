import logging
from typing import List
from data.schemas import Meme

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModerationModule:

    def __init__(self, enable_moderation: bool):
        self.enable_moderation = enable_moderation
        logger.info("ModerationModule initialized")

    def moderate_memes(self, memes: List[Meme]) -> List[Meme]:
        if not self.enable_moderation:
            return memes
        else:
            print("code not completed")
            return memes
