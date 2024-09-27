import requests
import os
from urllib.parse import urlencode
from utils.validators import HttpResponse
from data.schemas import MemeImage
from typing import Optional, List
from dotenv import load_dotenv


class ImgFlipAPI:
    BASE_URL = "https://api.imgflip.com"

    def __init__(self):
        load_dotenv()
        self.username = os.getenv('IMG_FLIP_API_USERNAME')
        self.password = os.getenv('IMG_FLIP_API_PASSWORD')

    def get_top100_used_meme_images(self) -> HttpResponse:
        url = f"{self.BASE_URL}/get_memes"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if data['success']:
                top_100_used_meme_images = []
                for m in data['data']['memes']:
                    meme_image = MemeImage(id=m.get("id"),
                                           name=m.get("name"),
                                           url=m.get("url"),
                                           width=m.get("width"),
                                           height=m.get("height"),
                                           box_count=m.get("box_count"),
                                           times_used=m.get("captions"))
                    top_100_used_meme_images.append(meme_image)
                return HttpResponse.success(data=top_100_used_meme_images)
            else:
                return HttpResponse.failure(message=data.get('error_message', 'Unknown error'))
        except requests.RequestException as e:
            return HttpResponse.failure(message=f"Error fetching meme templates: {str(e)}")

    '''
    [
   {
      "text": "One does not simply",
      "x": 10,
      "y": 10,
      "width": 548,
      "height": 100,
      "color": "#ffffff",
      "outline_color": "#000000"
   },
   {
      "text": "Make custom memes on the web via imgflip API",
      "x": 10,
      "y": 225,
      "width": 548,
      "height": 100,
      "color": "#ffffff",
      "outline_color": "#000000"
   }
    ]
    '''

    def caption_meme_image(self,
                           meme_image_id: int,
                           font: Optional[str] = "impact",
                           max_font_size: Optional[int] = 50,
                           captions: Optional[List[str]] = None,
                           no_watermark: bool = False) -> HttpResponse:
        url = f"{self.BASE_URL}/caption_image"

        data = {
            'template_id': meme_image_id,
            'username': self.username,
            'password': self.password,
            'font': font,
            'max_font_size': max_font_size
        }
        if len(captions) <= 2:
            data['text0'] = captions[0]
            data['text1'] = captions[1]
        else:
            data['boxes'] = []
            for caption in captions:
                data['boxes'].append({
                    'text': caption,
                })

        if no_watermark:
            data['no_watermark'] = True

        encoded_data = urlencode(data)

        try:
            response = requests.post(url, data=encoded_data,
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            response.raise_for_status()

            result = response.json()

            if result['success']:
                return HttpResponse.success(
                    data={'url': result['data']['url']},
                    message="Meme created successfully"
                )
            else:
                return HttpResponse.failure(
                    message=result.get('error_message')
                )

        except requests.RequestException as e:
            return HttpResponse.failure(
                message=f"An exception occured while the creating meme: {str(e)}",
                status_code=500
            )

    def get_meme_image(self,
                       meme_image_id: int) -> HttpResponse:

        url = f"{self.BASE_URL}/get_meme"

        data = {
            'template_id': meme_image_id,
            'username': self.username,
            'password': self.password,
        }

        encoded_data = urlencode(data)

        try:
            response = requests.get(url, data=encoded_data,
                                    headers={'Content-Type': 'application/x-www-form-urlencoded'})
            response.raise_for_status()

            result = response.json()

            if result['success']:
                meme_image = MemeImage(id=result['data']['meme']['id'],
                                       name=result['data']['meme']['name'],
                                       url=result['data']['meme']['url'],
                                       width=result['data']['meme']['width'],
                                       height=result['data']['meme']['height'],
                                       box_count=result['data']['meme']['box_count'],
                                       times_used=result['data']['meme']['captions'])  # all time
                return HttpResponse.success(
                    data={meme_image},
                    message="Meme created successfully"
                )
            else:
                return HttpResponse.failure(
                    message=result.get('error_message')
                )

        except requests.RequestException as e:
            return HttpResponse.failure(
                message=f"An exception occured while getting the meme: {str(e)}",
                status_code=500
            )


if __name__ == '__main__':
    api = ImgFlipAPI()
    response = api.get_top100_used_meme_images()
