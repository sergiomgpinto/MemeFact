import logging
from typing import List
from utils.img_flip_api import ImgFlipAPI
from dotenv import load_dotenv
from data.schemas import Meme


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConcatenationModule:

    def __init__(self):

        load_dotenv()
        self.img_flip_api = ImgFlipAPI()
        logger.info("ConcatenationModule initialized")

    def generate_memes(self, memes: List[Meme]) -> List[Meme]:

        updated_memes = memes

        for meme in updated_memes:
            meme_image = meme.get_meme_image()
            meme_captions = meme.get_captions()
            url = meme.get_url()

            if url:
                print(f'The meme has already an upload url {url}.')
            else:
                response = self.img_flip_api.caption_meme_image(meme_image_id=meme_image.get_id(),
                                                                captions=meme_captions)
                if response.get_is_success():
                    data = response.get_data()
                    meme.set_url(data['url'])
                    print(f'Meme upload url: {data['url']}')
                else:
                    print(f'Failed creating meme {meme_image.get_id()} with error: {response.get_message()}')
                    continue

        return updated_memes
