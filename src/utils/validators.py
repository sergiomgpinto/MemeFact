import requests
from pydantic import BaseModel
from typing import Optional, Any


class HttpResponse(BaseModel):
    status_code: int
    is_success: bool
    message: str
    data: Optional[Any] = None

    @classmethod
    def success(cls, data: Optional[Any] = None, status_code: int = 200, message: str = "Request successful"):
        return cls(status_code=status_code, is_success=True, message=message, data=data)

    @classmethod
    def failure(cls, message: str, status_code: int = 400, data: Optional[Any] = None):
        return cls(status_code=status_code, is_success=False, message=message, data=data)

    def get_is_success(self):
        return self.is_success

    def get_data(self):
        return self.data

    def get_message(self):
        return self.message


def validate_url(url: str) -> HttpResponse:
    try:
        response = requests.head(url, allow_redirects=True)
        if not response.ok:
            return HttpResponse.failure(status_code=response.status_code,
                                        message=f"URL {url} does not exist or is not accessible")
        return HttpResponse.success(status_code=response.status_code)
    except requests.RequestException as e:
        return HttpResponse.failure(status_code=500,
                                    message=f"Error validating URL {url}: {str(e)}")
