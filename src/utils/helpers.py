import base64
import subprocess
import httpx
import requests
import yaml
from data.schemas import Meme
from typing import List
from pathlib import Path
from datetime import datetime


def get_git_root() -> Path:
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'],
                                           stderr=subprocess.STDOUT).decode().strip()
        return Path(git_root)
    except subprocess.CalledProcessError:
        print("Warning: Not in a git repository. Using current working directory.")
        return Path.cwd()


def download_image(url: str, filename: str, save_directory: Path) -> str:
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        filename = filename.replace('/', '_')
        save_path = save_directory / (filename + ".png")

        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Saved meme at path: {save_path}")
        return str(save_path)

    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return ""


def download_meme_temp(url: str) -> str:
    root_dir = Path(get_git_root())
    temp_dir = root_dir / 'temp'
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    meme_filename = f'{url}_{timestamp}'
    temp_dir.mkdir(parents=True, exist_ok=True)

    return download_image(url, meme_filename, temp_dir)


def download_memes(memes: List[Meme], bot_run: bool):
    root_dir = Path(get_git_root())
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    num_memes = len(memes)

    if bot_run:
        base_dir = root_dir / 'data' / 'bot' / 'memes'
    else:
        base_dir = root_dir / 'output'

    batch_dir = base_dir / f"{num_memes}_memes_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    for index, meme in enumerate(memes, start=1):
        meme_filename = f'{index}_{meme.get_meme_image().get_name()}'
        download_image(meme.get_url(), meme_filename, batch_dir)


def load_config(config_file: str):
    git_root = get_git_root()
    path = git_root / 'config' / config_file
    with open(path, 'r') as file:
        return yaml.safe_load(file)


# def encode_image_base64(url: str):
#     return base64.b64encode(httpx.get(url).content).decode('utf-8')
def encode_image_base64(url: str):
    """Fetch image from URL and encode it as base64"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}  # Prevent Google from blocking the request
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()  # Raise an error if request fails

        # Convert response content to base64
        return base64.b64encode(response.content).decode('utf-8')

    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from URL: {url} - {e}")
        return None  # Return None if the image can't be fetched


def is_date_more_recent(new_date: str, starting_date: str) -> bool:
    date1_obj = datetime.strptime(new_date.strip(), "%B %d, %Y")
    date2_obj = datetime.strptime(starting_date.strip(), "%B %d, %Y")

    if date1_obj > date2_obj:
        return True
    else:
        return False
