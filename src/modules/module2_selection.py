import logging
from modules.module1_input import InputModule
from rag.vector_db import VectorDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SelectionModule:

    def __init__(self, input_module: InputModule):
        self.input_module = input_module
        self.vector_db = VectorDB()
        logger.info("SelectionModule initialized")

    def rag(self, num_memes: int):
        input_data = self.input_module.get_input()
        article = input_data.get_article()
        meme_image = input_data.get_meme_images()

        if not meme_image:
            article_data = {
                'claim': article.get_claim(),
            }

            if article.get_iytis():
                article_data['iytis'] = article.get_iytis()
            if article.get_title():
                article_data['title'] = article.get_title()
            if article.get_verdict():
                article_data['verdict'] = article.get_verdict()
            if not article.get_iytis() and article.get_rationale():
                article_data['rationale'] = article.get_rationale()

            return self.vector_db.query(None, article_data, num_memes)
        else:
            return self.vector_db.query(str(meme_image[0].get_id()), None, num_memes)
