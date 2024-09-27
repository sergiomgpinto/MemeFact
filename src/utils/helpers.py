import base64
import requests
import os
import httpx
from pydantic import HttpUrl
from data.schemas import Meme
from typing import List


def download_image(url: str, filename: str, save_directory: str = "output") -> str:
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs(save_directory, exist_ok=True)

        filename = filename.replace('/', '_')

        save_path = os.path.join(save_directory, filename + ".png")
        print(save_path)
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return save_path

    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return ""


def download_memes(memes: List[Meme]):
    for meme in memes:
        meme_file_name = meme.get_url()
        download_image(meme.get_url(), meme_file_name)


def url_to_data_url(url: HttpUrl) -> str:
    # Convert HttpUrl to string if necessary
    url_string = str(url)

    # Fetch the image
    response = httpx.get(url_string)
    response.raise_for_status()  # This will raise an exception for HTTP errors
    #print(response.content)
    # Get the content type
    content_type = response.headers.get('content-type', 'image/jpeg')

    # Encode the image content to base64
    base64_image = base64.b64encode(response.content).decode('utf-8')

    # Create the data URL
    data_url = f'data:{content_type};base64,{base64_image}'
    #print(data_url)
    return data_url
