import logging
from modules.module1_input import InputModule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SelectionModule:

    def __init__(self, input_module: InputModule):
        self.input_module = input_module
        logger.info("SelectionModule initialized")

    def rag(self):
        input_data = self.input_module.get_input()
        article = input_data.get_article()
        meme_image = input_data.get_meme_images()

        if not meme_image:
            pass
        else:
            pass
