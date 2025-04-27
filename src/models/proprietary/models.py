import os
import time
import random
import google.generativeai as genai
from abc import ABC
from typing import override
from models.model import BaseModel, ModelParameters, parse_content_prefix
from models.prompt import Prompt
from utils.helpers import encode_image_base64
from openai import OpenAI, OpenAIError
from tenacity import retry, stop_after_attempt, wait_random_exponential
import numpy as np
import httpx
import base64
import mimetypes


def _format_token_probabilities(response):
    """
    Reassembles the category name from consecutive tokens until encountering a literal ':',
    then checks if that reassembled category is one of:
        coherence, clarity, hilarity, persuasiveness, template_appropriateness.
    If it matches, it looks at the subsequent tokens for the pattern:
        ' ' -> digit -> '/' -> '5'
    and captures the probability of the digit token for that category.
    Finally, returns an average of all 5 probabilities if found.
    """

    # Retrieve token logprobs
    content_logprobs = response.choices[0].logprobs.content
    if not content_logprobs:
        print("[DEBUG] No logprobs available in the response.")
        return "No logprobs available in the response."

    categories_of_interest = {
        'coherence': None,
        'clarity': None,
        'hilarity': None,
        'persuasiveness': None,
        'template_appropriateness': None
    }

    #print("[DEBUG] Rebuilding category names from tokens. Searching for scores...")

    # We'll accumulate potential category text into this buffer
    category_buffer = []
    pending_category = None

    # Index-based loop so we can look ahead for the " digit / 5" pattern
    i = 0
    n = len(content_logprobs)

    while i < n:
        token = content_logprobs[i].token

        # Check if the token is exactly a colon
        if token.strip() == ':':
            # We've reached the end of a potential category name
            # Reassemble all partial tokens into one string
            candidate_text = "".join(category_buffer).strip().lower()
            category_buffer.clear()  # reset

            # Check if our candidate_text is in the categories list
            if candidate_text in categories_of_interest:
                pending_category = candidate_text
                #print(f"[DEBUG] Found category: '{pending_category}'. Checking for next pattern ' digit / 5'...")

                # The next tokens should be: ' ' -> [digit 1–5] -> '/' -> '5'
                # We'll look ahead carefully, ensuring we don't go out of bounds
                # pattern = (i+1): ' '  (i+2): digit  (i+3): '/'  (i+4): '5'
                # Then we store the probability of that digit token
                if i + 4 < n:
                    # i+1 => space
                    space_tok = content_logprobs[i + 1].token.strip()
                    # i+2 => digit
                    digit_tok = content_logprobs[i + 2].token.strip()
                    digit_logprob = content_logprobs[i + 2].logprob
                    # i+3 => slash
                    slash_tok = content_logprobs[i + 3].token.strip()
                    # i+4 => '5'
                    five_tok = content_logprobs[i + 4].token.strip()

                    if (space_tok == '' and
                            digit_tok.isdigit() and
                            slash_tok == '/' and
                            five_tok == '5'):

                        # parse the digit
                        val = int(digit_tok)
                        if 1 <= val <= 5:
                            prob = np.exp(digit_logprob) * 100
                            categories_of_interest[pending_category] = prob
                            #print(f"[DEBUG]    -> Score = {val}/5 with probability {prob:.2f}%")
                            # skip ahead by 4, because we consumed those tokens
                            i += 4
                        else:
                            pass
                            #print(f"[DEBUG]    -> Score token '{digit_tok}' out of 1–5 range.")
                    else:
                        pass
                        #print(f"[DEBUG]    -> Pattern mismatch after '{pending_category}:'; not ' digit / 5'.")

                # Reset pending_category
                pending_category = None

            else:
                # Not a recognized category, just ignore
                category_buffer.clear()

        else:
            # Accumulate partial text (strip leading/trailing spaces from each piece)
            # We remove newline or random whitespace in tokens, but keep underscores, letters, etc.
            part = token.strip()
            # If there's something non-empty, accumulate it:
            if part:
                category_buffer.append(part)

        i += 1

    # Now gather the probabilities for whichever categories were found
    found_probs = [p for p in categories_of_interest.values() if p is not None]
    found_count = len(found_probs)

    #print(f"[DEBUG] Completed parsing. Categories found: {found_count}/5")

    if found_count < 5:
        return (
            "Not all five scores could be identified. "
            f"Found probabilities for {found_count} category(ies): {found_probs}"
        )

    avg_confidence = sum(found_probs) / 5.0
    #print(f"[DEBUG] Average confidence across the 5 scoring tokens: {avg_confidence:.2f}%")
    return f"{avg_confidence:.2f}%"


class ProprietaryModel(BaseModel, ABC):

    def __init__(self, client, params: ModelParameters, parse: bool):
        self.client = client
        self.params = params
        self.parse = parse

    def prepare_params(self, model_name, **params):
        final_params = self.params.to_dict(model_name).copy()

        if 'mode' in params:
            mode = params.pop('mode')
            if mode == 'deterministic':
                params['temperature'] = 0.2
            elif mode == 'creative':
                params['temperature'] = 0.7
            else:
                raise ValueError("Mode must be either 'deterministic' or 'creative'")

        if model_name == 'gpt-4o':
            params['logprobs'] = True
            params['top_logprobs'] = 5

        final_params.update(params)
        print(f'API Call Params:{final_params}')
        return final_params


class Gpt4o(ProprietaryModel):

    def __init__(self, params, parse):
        super().__init__(OpenAI(api_key=os.getenv("OPENAI_API_KEY")), params, parse)

    def _parse_response(self, response):
        return parse_content_prefix(response.choices[0].message.content.strip())

    @override
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
    def prompt(self, prompt: Prompt, **params):
        image = prompt.get_image()
        content = [{"type": "text", "text": prompt.get_text()}]
        try:
            if image:
                if isinstance(image, list):
                    for img_url in image:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": img_url}
                        })
                elif isinstance(image, str):
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": image}
                    })
            params = {
                "model": "gpt-4o-2024-11-20",
                "messages": [{"role": "user", "content": content}],
                **self.prepare_params('gpt-4o', **params)
            }
            response = self.client.chat.completions.create(**params)
            real_confidence = _format_token_probabilities(response)

            return self._parse_response(response) if self.parse else response.choices[0].message.content.strip(), real_confidence
        except OpenAIError as e:
            print(e)
            return []
        except Exception as e:
            print(e)
            return []


class GeminiPro(ProprietaryModel):
    def __init__(self, params, parse):
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        super().__init__(genai, params, parse)

    def _parse_response(self, response):
        return parse_content_prefix(response.text)

    @override
    def prompt(self, prompt: Prompt, **params):
        image = prompt.get_image()
        try:
            time.sleep(random.uniform(0.5, 1.5))
            model = self.client.GenerativeModel(model_name='gemini-1.5-pro-002')
            contents = [prompt.get_text()]

            if image:
                image_parts = []
                if isinstance(image, list):
                    for img_url in image:
                        response = httpx.get(img_url, headers={"User-Agent": "Mozilla/5.0"})
                        if response.status_code == 200:
                            # Get the correct MIME type
                            mime_type = mimetypes.guess_type(img_url)[0]
                            if mime_type == "image/jpg":  # Convert jpg to jpeg
                                mime_type = "image/jpeg"

                            image_parts.append({
                                'mime_type': mime_type,
                                'data': base64.b64encode(response.content).decode('utf-8')
                            })
                elif isinstance(image, str):
                    response = httpx.get(image)
                    if response.status_code == 200:
                        # Get the correct MIME type
                        mime_type = mimetypes.guess_type(image)[0]
                        if mime_type == "image/jpg":  # Convert jpg to jpeg
                            mime_type = "image/jpeg"

                        image_parts = [{
                            'mime_type': mime_type,
                            'data': base64.b64encode(response.content).decode('utf-8')
                        }]
                # Append the processed images to contents
                contents += image_parts
            response = model.generate_content(contents=contents, generation_config={**self.prepare_params('gemini-1.5-pro', **params)})

            return self._parse_response(response) if self.parse else response.text
        except Exception as e:
            print(f"Error in GeminiPro prompt: {e}")
            return []


class ClaudeSonnet(ProprietaryModel):

    def __init__(self, params, parse):
        from anthropic import Anthropic
        super().__init__(Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')), params, parse)

    def _parse_response(self, response):
        return parse_content_prefix(response.content[0].text)

    @override
    def prompt(self, prompt: Prompt, **params):
        image = prompt.get_image()
        try:
            messages = [{"role": "user", "content": [{"type": "text", "text": prompt.get_text()}]}]
            if image:
                if isinstance(image, list):
                    for img in image:
                        messages[0]["content"].append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": encode_image_base64(img)
                            }
                        })
                elif isinstance(image, str):
                    messages[0]["content"].append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encode_image_base64(image)
                        }
                    })
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                messages=messages,
                **self.prepare_params('claude-3.5-sonnet', **params)
            )
            return self._parse_response(response) if self.parse else response.content[0].text
        except Exception as e:
            print(f"Error in ClaudeSonnet prompt: {e}")
            return []
