import logging
import os
from openai import OpenAI
from rag.knowledge_graph import prompt_gpt4o, load_config
from rag.testing import KYMScraper
from rag.vector_db import VectorDB
from utils.img_flip_api import ImgFlipAPI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_content(lines):
    sections = {}
    current_number = None
    current_content = []
    lines = lines.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith(('1:', '2:', '3:', '4:', '5:')):
            if current_number:
                sections[current_number] = ' '.join(current_content)
                current_content = []
            current_number = line[0]
            current_content.append(line[3:])
        elif current_number:
            current_content.append(line)

    if current_number and current_content:
        sections[current_number] = ' '.join(current_content)

    return sections


def _process_captions(captions):
    examples = captions.split('|||')

    formatted_examples = []
    for i, example in enumerate(examples, 1):
        variations = example.strip().split(';')
        formatted_variations = [f"Text box {j}: {var.strip()}"
                                for j, var in enumerate(variations, 1)]
        formatted_example = f"Example {i}:\n" + "\n".join(formatted_variations)
        formatted_examples.append(formatted_example)

    return "\n\n".join(formatted_examples)


def _generate_description(prompt_text, url, client, no_input_image):
    row = {
        "template_url": url,
    }
    content = prompt_gpt4o(prompt_text, row, client, no_input_image)
    if not content:
        return None
    else:
        return content


class Pipeline:

    def __init__(self):
        self.db = VectorDB()
        self.api = ImgFlipAPI()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.scraper = KYMScraper()
        self.config = load_config('imkg.yaml')

    def run(self):

        while True:
            meme_id = input('Enter imgflip meme id or exit: ')

            if meme_id == 'exit':
                return

            response = self.api.get_meme_image(int(meme_id))

            # get meme data from imgflip api
            if not response.get_is_success():
                logger.info(f"Error fetching meme image with id {meme_id}: {response.get_message()}")
            meme = response.get_data()
            print(f"Meme: {meme}")
            # get about section if there is a KYM entry
            # kym_meme_entry = input('Enter KYM url meme entry: ')
            # about_text = ''
            # if kym_meme_entry != 'q':
            #     about_text = self.scraper.get_about_section(kym_meme_entry)
            # print(f"About text before: {about_text}")
            # prompt = """Fix spacing between words and around punctuation for the given string of text: {about_text}."""
            # prompt = prompt.format(about_text=about_text)
            # row = {
            #     "template_url": meme.get_url(),
            # }
            # about_text_corrected = prompt_gpt4o(prompt, row, self.client, False)
            # print(f"About text after: {about_text_corrected}")
            # about_text = about_text_corrected
            about_text = input('Enter about text or q: ')
            if about_text == 'q':
                continue
            # generate visual description
            description = _generate_description(self.config['prompt_meme_description'], str(meme.get_url()), self.client, False)
            if not description:
                logger.info(f"Error generating description for meme {meme_id}")
                continue

            print(f"Description before: {description}")
            description = _parse_content(description)
            strings = []
            for key, value in description.items():
                strings.append(value)
            description = ' '.join(strings)
            print(f"Description: {description}")

            # get captions, views and upvotes
            captions = []
            views = 0
            upvotes = 0
            counter = 0
            while True:
                meme_captions = input('Enter captions or q: ')
                if meme_captions == 'q':
                    break
                captions.append(meme_captions)
                meme_views = input('Enter views : ')
                meme_upvotes = input('Enter upvotes : ')
                views += int(meme_views)
                upvotes += int(meme_upvotes)
                counter += 1
                print(f'Number of memes scraped: {counter}')

            # generate captioning style explanation
            captions = ' ||| '.join(captions)
            print(f'Captions: {captions}')
            processed_captions = _process_captions(captions)
            print(f'Processed captions: {processed_captions}')
            inputs = {
                'meme_captions': processed_captions,
                'meme_image_description': description,
            }

            caption_style_explanation = _generate_description(self.config['prompt_meme_explanation'].format(**inputs),
                                                              str(meme.get_url()),
                                                              self.client, True)
            caption_style_explanation = _parse_content(caption_style_explanation)
            strings = []
            for key, value in caption_style_explanation.items():
                strings.append(value)
            caption_style_explanation = ' '.join(strings)
            print(f'Captions: {captions}')
            print(f'Caption style explanation: {caption_style_explanation}')
            print(f'Views: {views}')
            print(f'Upvotes: {upvotes}')
            self.db.add_entry(meme_template_id=meme_id,
                              template_title=meme.get_name(),
                              about=about_text,
                              description=description,
                              captions=captions,
                              caption_style_explanation=caption_style_explanation,
                              box_count=meme.get_box_count(),
                              url=str(meme.get_url()),
                              total_views=views,
                              total_upvotes=upvotes)


if __name__ == '__main__':
    pipeline = Pipeline()
    pipeline.run()
