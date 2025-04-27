import logging
from typing import List
from data.schemas import Meme
from models.hmd import HatefulMemeDetectionModel
from utils.helpers import download_meme_temp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModerationModule:

    def __init__(self, enable_moderation: bool):
        self.enable_moderation = enable_moderation
        logger.info("ModerationModule initialized")
        if self.enable_moderation:
            self.hmd = HatefulMemeDetectionModel()

    def moderate_memes(self, memes: List[Meme]) -> List[Meme]:
        if not self.enable_moderation:
            return memes
        else:
            for meme in memes:
                url = meme.get_url()
                meme_temp_path = download_meme_temp(url)
                if self.hmd.detect(meme_temp_path):
                    meme.set_hateful()
            return memes
