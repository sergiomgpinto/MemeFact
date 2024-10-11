import pandas as pd
import os
import glob
from pathlib import Path
from utils.img_flip_api import ImgFlipAPI
from utils.helpers import download_image
from data.csv import data_to_csv


class MemesDataManager:

    def __init__(self):
        self.img_flip_api = ImgFlipAPI()
        self.memes_data = self._load_memes_data()

    def get_random_meme_image_url(self, num_memes):
        sampled_memes = self.memes_data.sample(n=num_memes)
        return sampled_memes['url'].tolist()

    def _load_memes_data(self):
        pattern = os.path.join(Path.cwd() / '..' / '..' / 'data' / 'raw', "meme_images_*.csv")
        csv_files = glob.glob(pattern)
        if not csv_files:
            self.fetch_and_store_meme_data()

        latest_csv = max(csv_files, key=os.path.getmtime)

        try:
            df = pd.read_csv(latest_csv)
            return df
        except Exception as e:
            print(f'Error loading memes: {e}')

    def get_meme_by_id(self, meme_id):
        return self.memes_data[self.memes_data['id'] == meme_id]

    def get_meme_by_name(self, meme_name):
        return self.memes_data[self.memes_data['name'] == meme_name]

    def get_meme_by_url(self, meme_url):
        return self.memes_data[self.memes_data['url'] == meme_url]

    def fetch_and_store_meme_data(self):

        response = self.img_flip_api.get_top100_used_meme_images()
        ids = []
        names = []
        urls = []
        widths = []
        heights = []
        box_counts = []
        times_useds = []

        if not response.get_is_success():
            print(f'Failed to fetch top 100 meme images from ImgFlip: {response.get_message()}')
            return

        data = response.get_data()
        for meme in data:
            ids.append(meme.get_id())
            names.append(meme.get_name())
            urls.append(meme.get_url())
            widths.append(meme.get_width())
            heights.append(meme.get_height())
            box_counts.append(meme.get_box_count())
            times_useds.append(meme.get_times_used())

        data_to_csv("meme_images",
                    id=ids,
                    name=names,
                    url=urls,
                    width=widths,
                    height=heights,
                    box_count=box_counts,
                    times_used=times_useds)

        for meme_url, meme_name in zip(urls, names):
            download_image(meme_url, meme_name, f'../../data/raw/meme_images')
