import logging
import os
import pandas as pd
from typing import Any
from data.schemas import InputData, FactCheckingArticle, MemeImage
from utils.validators import validate_url
from data.scrape_politifact import politifact_specific_article_scraper
from data.img_flip_memes import MemesDataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParserError(Exception):

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"ParserError: {self.message}"


class InputParser:

    def __init__(self, args: Any):
        self.article_source = args['politifact']
        self.meme_image_sources = args['meme_images']
        self.meme_data_manager = MemesDataManager()
        self.variant = args['variant']

    def parse(self):
        input_data = InputData()

        if self.variant == "baseline" and not self.meme_image_sources:
            raise ParserError("Baseline variant requires a meme image")

        if not isinstance(self.article_source, str):
            raise ParserError("Invalid politifact source. Must be a URL, /path/to/txt/file, or "
                              "'/path/to/csv/file:index'.")

        if self.article_source.startswith('https://www.politifact.com/factchecks/'):
            # Article source is a url.
            response = validate_url(self.article_source)
            if response.get_is_success():
                article = self.url_to_article()
                input_data.set_article(article)
            else:
                raise ParserError(response.get_message())
        elif ':' in self.article_source:
            # Article source is a csv file.
            article_path, index = self.article_source.rsplit(':', 1)
            self.article_source = article_path
            if not os.path.isfile(article_path):
                raise ParserError("There does not exist a csv file at the path given.")
            if not self.article_source.lower().endswith('.csv'):
                raise ParserError("File is not a csv.")
            if not index.isdigit() or int(index) < 0:
                raise ParserError("The index must be a positive 0 included integer.")
            article = self.csv_to_article(int(index))
            input_data.set_article(article)
        else:
            raise ParserError("Invalid article source.")

        if self.meme_image_sources:
            for source in self.meme_image_sources:
                meme_image = self.parse_single_meme_source(source)
                input_data.append_meme_image(meme_image)

        logger.info("Arguments parsed successfully")
        return input_data

    def parse_single_meme_source(self, source):
        if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
            # Meme image source is an ImgFlip meme image id.
            return self.meme_image_id_to_meme_image(int(source))
        elif isinstance(source, str):
            if source.startswith('https://'):
                # Meme image source is an ImgFlip url.
                return self.url_to_meme_image(source)
            else:
                # Meme image source is an ImgFlip meme image name.
                return self.meme_image_name_to_meme_image(source)
        else:
            raise ParserError(f"Invalid meme image source: {source}")

    def csv_to_article(self, row_index):
        df = pd.read_csv(self.article_source)
        if row_index >= len(df):
            raise ParserError(f'Invalid row index: {row_index}. File has {len(df)} rows.')

        article_data = df.iloc[row_index].to_dict()

        return FactCheckingArticle(claim=article_data['claim'],
                                   verdict=article_data['verdict'],
                                   rationale=article_data['rationale'],
                                   iytis=article_data['iytis'],
                                   source=article_data['source'],
                                   date=article_data['date'])

    def url_to_article(self):
        article_dict = politifact_specific_article_scraper(self.article_source, True)[0]
        if not article_dict:
            raise ParserError(f'Could not scrape article from URL: {self.article_source}')
        return FactCheckingArticle(claim=article_dict['claim'],
                                   verdict=article_dict['verdict'],
                                   rationale=article_dict['rationale'],
                                   iytis=article_dict['iytis'],
                                   url=self.article_source,
                                   source=article_dict['source'],
                                   date=article_dict['date'])

    def meme_image_id_to_meme_image(self, meme_id):
        meme_info = self.meme_data_manager.get_meme_by_id(meme_id)
        meme_info = meme_info.iloc[0].to_dict()

        return MemeImage(**meme_info)

    def url_to_meme_image(self, url):
        meme_info = self.meme_data_manager.get_meme_by_url(url)
        meme_info = meme_info.iloc[0].to_dict()

        return MemeImage(**meme_info)

    def meme_image_name_to_meme_image(self, name):
        meme_info = self.meme_data_manager.get_meme_by_name(name)
        meme_info = meme_info.iloc[0].to_dict()

        return MemeImage(**meme_info)
