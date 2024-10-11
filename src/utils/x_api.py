import os
import re
from dotenv import load_dotenv
from data.schemas import Meme
from pytwitter import Api
from utils.helpers import encode_image_base64


def _parse_tweet_id_from_tweet_url(url: str) -> str:
    pattern = r'https://x\.com/[A-Za-z0-9]+.*/status/[0-9]+'

    match = re.search(pattern, url)
    if match:
        return url.split('/')[-1]
    else:
        return ''


def parse_username(url: str) -> str:
    pattern = r'https://x\.com/[A-Za-z0-9]+.*/[A-Za-z]+/[0-9]+'

    match = re.search(pattern, url)
    if match:
        return url.split('/')[-3]
    else:
        return ''


class XApi:

    def __init__(self):
        load_dotenv()
        self.api = Api(consumer_key=os.getenv('TWITTER_API_KEY'),
                       consumer_secret=os.getenv('TWITTER_API_KEY_SECRET'),
                       access_token=os.getenv('TWITTER_API_ACCESS_TOKEN'),
                       access_secret=os.getenv('TWITTER_API_ACCESS_SECRET'))

    def _upload_meme_to_x(self, meme: Meme) -> int:
        url = meme.get_url()
        encoded_image = encode_image_base64(url)
        response = self.api.upload_media_simple(media_data=encoded_image, media_category='tweet_image',
                                                return_json=True)
        return response.get('media_id')

    def _create_disclaimer_tweet(self, text: str, tweet_id: str):
        return self.api.create_tweet(text=text,
                                     reply_in_reply_to_tweet_id=tweet_id,
                                     return_json=True)

    def _create_meme_tweet(self, source_tweet_url: str, meme: Meme):
        tweet_id = _parse_tweet_id_from_tweet_url(source_tweet_url)
        meme_id = self._upload_meme_to_x(meme)

        if not tweet_id:
            print(f'Invalid tweet link: {source_tweet_url}.')
            return {}
        if not meme_id:
            print(f'Failed uploading meme to X API: {meme}.')
            return {}

        return self.api.create_tweet(reply_in_reply_to_tweet_id=str(tweet_id),
                                     media_media_ids=[str(meme_id)], return_json=True)

    def create_tweet(self, is_meme_tweet: bool, post_text: str = None, meme_tweet_id: int = None,
                     meme: Meme = None, source_tweet_url: str = None):

        if is_meme_tweet:
            response = self._create_meme_tweet(source_tweet_url=source_tweet_url, meme=meme)
        else:
            response = self._create_disclaimer_tweet(text=post_text, tweet_id=str(meme_tweet_id))
        return response

    def create_post(self, source_tweet_url: str, meme: Meme, post_text: str):
        first_response = self.create_tweet(is_meme_tweet=True, source_tweet_url=source_tweet_url, meme=meme)

        if not first_response['data']:
            return {}
        else:
            first_call_data = first_response['data']
            second_response = self.create_tweet(is_meme_tweet=False,
                                                meme=meme, post_text=post_text, meme_tweet_id=first_call_data['id'])
            second_call_data = second_response['data']
            return {'meme_post_response_data': first_call_data, 'disclaimer_post_response_data': second_call_data}
