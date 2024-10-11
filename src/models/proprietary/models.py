import os
import google.generativeai as genai
from models.model import ProprietaryModel
from models.prompt import Prompt
from utils.helpers import encode_image_base64
from openai import OpenAI, OpenAIError
from tenacity import retry, stop_after_attempt, wait_random_exponential


def _parse_captions_prefix(content: str):
    captions = []
    lines = content.split('\n')
    print("*****Generated captions*****")
    for line in lines:
        if line.startswith('Caption'):
            print(line)
            caption = line.split(':', 1)[1].strip().strip('"')
            captions.append(caption)
        else:
            print(f"The line '{line}' does not start with the required prefix. Skipping...")
    print("*****End generated captions*****")
    return captions


class Gpt4o(ProprietaryModel):

    def __init__(self):
        super().__init__(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))

    def _parse_response(self, response):
        if not response.choices:
            raise OpenAIError('Gpt4o did not provide any answer.')
        content = response.choices[0].message.content.strip()

        refusal_indicators = [
            "I'm sorry, but I can't",
            "I don't have information about",
            "I'm not able to",
            "I cannot provide",
            "I'm not comfortable",
            "I don't have access to",
            "I'm not authorized to",
        ]

        if any(indicator.lower() in content.lower() for indicator in refusal_indicators):
            raise OpenAIError("The model refused to answer.")
        return _parse_captions_prefix(content)

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def prompt(self, prompt: Prompt):
        image = prompt.get_image()

        content = [{"type": "text", "text": prompt.get_text()}]
        try:
            if image:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image}
                })
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                max_tokens=300
            )
            return self._parse_response(response)
        except OpenAIError as e:
            print(e)
            return []
        except Exception as e:
            print(e)
            return []


class GeminiPro(ProprietaryModel):
    def __init__(self):
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        super().__init__(genai)

    def _parse_response(self, response):
        return _parse_captions_prefix(response.text)

    def prompt(self, prompt: Prompt):
        image = prompt.get_image()
        try:
            model = self.client.GenerativeModel(model_name='gemini-1.5-pro-002')
            contents = [prompt.get_text()]
            if image:
                file = genai.upload_file(path=f'data/raw/meme_images/{image}.png',
                                         display_name=image)
                contents.append(file)
            response = model.generate_content(contents)
            return self._parse_response(response)
        except Exception as e:
            print(f"Error in GeminiPro prompt: {e}")
            return []


class ClaudeSonnet(ProprietaryModel):

    def __init__(self):
        from anthropic import Anthropic
        super().__init__(Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')))

    def _parse_response(self, response):
        return _parse_captions_prefix(response.content[0].text)

    def prompt(self, prompt: Prompt):
        image = prompt.get_image()
        try:
            messages = [
                {
                    "role": "user",
                    "content": []
                }
            ]

            # Add text content
            messages[0]["content"].append(
                {
                    "type": "text",
                    "text": prompt.get_text()
                }
            )
            if image:
                messages[0]["content"].append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encode_image_base64(image)
                        }
                    }
                )
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                temperature=0,
                messages=messages
            )
            return self._parse_response(response)
        except Exception as e:
            print(f"Error in ClaudeSonnet prompt: {e}")
            return []
