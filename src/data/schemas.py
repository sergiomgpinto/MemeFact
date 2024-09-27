from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from utils.validators import validate_url


class FactCheckingArticle(BaseModel):
    claim: str
    verdict: str
    rationale: str
    source: str = None
    date: str = None
    iytis: Optional[str] = None
    url: Optional[HttpUrl] = None

    def get_claim(self) -> str:
        return self.claim

    def get_verdict(self) -> str:
        return self.verdict

    def get_rationale(self) -> str:
        return self.rationale

    def get_source(self) -> str:
        return self.source

    def get_date(self) -> str:
        return self.date

    def get_iytis(self) -> Optional[str]:
        return self.iytis

    def get_url(self) -> Optional[HttpUrl]:
        return self.url

    def validate_url_on_demand(self) -> 'FactCheckingArticle':
        if self.url:
            result = validate_url(str(self.url))
            if not result.is_success:
                raise ValueError(f"Invalid URL for FactCheckingArticle: {result.message}")
        return self


class MemeImage(BaseModel):
    id: int
    name: str
    url: HttpUrl
    width: int
    height: int
    box_count: int
    times_used: int  # How many times this meme image was captioned in the last 30 days.

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_url(self):
        return self.url

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_box_count(self):
        return self.box_count

    def get_times_used(self):
        return self.times_used

    def validate_url_on_demand(self) -> 'MemeImage':
        if self.url:
            result = validate_url(str(self.url))
            if not result.is_success:
                raise ValueError(f"Invalid URL for FactCheckingArticle: {result.message}")
        return self


class Meme(BaseModel):
    meme_image: MemeImage
    captions: List[str] = None
    url: HttpUrl = None
    hateful: bool = False

    def get_captions(self):
        return self.captions

    def get_meme_image(self):
        return self.meme_image

    def get_url(self):
        return self.url

    def set_url(self, url):
        self.url = url

    def set_hateful(self):
        self.hateful = True

    def is_hateful(self):
        return self.hateful


class InputData(BaseModel):
    article: FactCheckingArticle = None
    meme_image: Optional[MemeImage] = None

    def get_article(self):
        return self.article

    def get_meme_image(self):
        return self.meme_image

    def set_article(self, article):
        self.article = article

    def set_meme_image(self, meme_image):
        self.meme_image = meme_image
