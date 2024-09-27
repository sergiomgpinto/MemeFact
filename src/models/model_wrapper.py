import os
from dotenv import load_dotenv
from openai import OpenAI


class ModelWrapper:
    def __init__(self):
        load_dotenv()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

    def get_gpt4o(self):
        return OpenAI(api_key=self.openai_api_key)

    def send_message(self, model, claim, verdict, iytis, meme_image_url, box_count):
        prompt_text = f"""You are an AI assistant tasked with creating humorous and informative meme captions based on fact-checking articles. Please analyze the following information and generate appropriate meme captions:

    Claim: {claim}

    Verdict: {verdict}

    If Your Time Is Short: {iytis}

    This meme image requires {box_count} caption{'s' if box_count > 1 else ''}.

    Based on this information, please create {box_count} distinct caption{'s' if box_count > 1 else ''} for the meme that:
    1. Accurately reflects the fact-check's conclusion
    2. Is humorous or witty
    3. Fits the style and context of the meme image provided
    4. Each caption is concise and impactful (ideally no more than 15 words each)

    Generate the meme caption{'s' if box_count > 1 else ''} now. Present each caption on a new line, preceded by 'Caption X:', where X is the caption number."""

        response = model.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": str(meme_image_url),
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )

        captions = self._parse_captions(response.choices[0].message.content, box_count)

        return captions

    def _parse_captions(self, response_content, expected_count):
        lines = response_content.split('\n')
        captions = []
        for line in lines:
            if line.startswith('Caption'):
                caption_text = line.split(':', 1)[1].strip()
                captions.append(caption_text)

        if len(captions) != expected_count:
            raise ValueError(f"Expected {expected_count} captions, but got {len(captions)}")

        return captions
