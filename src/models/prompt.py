import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict
from utils.helpers import load_config


def _parse_meme_examples(params):
    parsed_meme_examples = []
    if 'meme_image_instances' in params:
        meme_examples = params['meme_image_instances']
        meme_examples = meme_examples.split('|||')

        for example in meme_examples:
            captions = example.split(';')
            captions = [caption.strip() for caption in captions]
            if not len(captions) > params['box_count']:
                parsed_meme_examples.append(captions)
        return parsed_meme_examples


@dataclass
class FieldConfig:
    description: str
    format_template: str


class PromptManager:

    def __init__(self, model, model_name):
        self.model = model
        self.prompt_config = load_config('prompts.yaml')
        self.promptTypes = {
            'zero-shot': lambda prompt_params:
            ZeroShotPrompt(self.prompt_config, prompt_params, model_name),
            'few-shot': lambda prompt_params:
            FewShotPrompt(self.prompt_config, prompt_params, model_name),
            'cot': lambda prompt_params:
            CotPrompt(self.prompt_config, prompt_params, model_name),
            'cov': lambda prompt_params, step, context:
            CovPrompt(self.prompt_config, prompt_params, model_name, step, context),
            'clot': lambda prompt_params, step, context:
            ClotPrompt(self.prompt_config, prompt_params, model_name, step, context),
            'debate-evaluate': lambda prompt_params:
            DebateEvaluatePrompt(self.prompt_config, prompt_params, model_name),
            'debate-improved-generation': lambda prompt_params:
            DebateImprovedGenerationPrompt(self.prompt_config, prompt_params, model_name),
            'debate-final-evaluate': lambda prompt_params:
            DebateFinalEvaluatePrompt(self.prompt_config, prompt_params, model_name),
            'llm-judge-study': lambda prompt_params:
            LlmJudgeStudyPrompt(self.prompt_config, prompt_params, model_name),
        }

    def generate_prompt(self, prompt_type, prompt_params, **params):
        def get_mode_for_step(prompt_type, step):
            creative_steps = {
                'cov': ['baseline', 'final_response'],
                'clot': ['association_thinking']
            }
            return 'creative' if step in creative_steps.get(prompt_type, []) else 'deterministic'

        if prompt_type == 'cov':
            verification_context = {}
            for step in ['baseline', 'plan_verification', 'execute_verification', 'final_response']:
                step_params = params.copy()
                step_params['mode'] = get_mode_for_step('cov', step)

                if step == 'final_response':
                    return self.model.prompt(self.promptTypes[prompt_type](prompt_params, step, verification_context),
                                             **step_params)
                else:
                    ret = self.model.prompt(self.promptTypes[prompt_type](prompt_params, step, verification_context),
                                            **step_params)
                    if not ret:
                        return []
                    verification_context[step] = ret
        elif prompt_type == 'clot':
            context = []
            for step in ['association_thinking', 'self_refinement']:
                step_params = params.copy()
                step_params['mode'] = get_mode_for_step('cov', step)

                if step == 'self_refinement':
                    return self.model.prompt(self.promptTypes[prompt_type](prompt_params, step, context),
                                             **step_params)
                else:
                    ret = self.model.prompt(self.promptTypes[prompt_type](prompt_params, step, context),
                                            **step_params)
                    if not ret:
                        return []
                    captions = []
                    for content in ret:
                        if not content.startswith('Reasoning'):
                            captions.append(content)
                        else:
                            context.append({'captions': captions, 'reasoning': content.split(': ')[1].strip()})
                            captions = []
        else:
            return self.model.prompt(self.promptTypes[prompt_type](prompt_params), **params)


class Prompt(ABC):

    def __init__(self, config: Dict, params: dict, model: str, step):
        self.class_name = re.sub(r'(?<!^)(?=[A-Z])', '-',
                                 self.__class__.__name__.split('Prompt')[0]).lower()
        self.field_config = {
            'claim': FieldConfig(
                description="The statement that was fact-checked.",
                format_template="Claim: {}"
            ),
            'verdict': FieldConfig(
                description="The fact-checker's conclusion about the claim's accuracy.",
                format_template="Verdict: {}"
            ),
            'iytis': FieldConfig(
                description="A brief summary of the key findings from the complete analysis.",
                format_template="If-your-time-is-short: {}"
            ),
            'rationale': FieldConfig(
                description="The complete analysis and evidence.",
                format_template="Full Rationale: {}"
            ),
            'title': FieldConfig(
                description="The fact-checking article's headline.",
                format_template="Title: {}"
            ),
            'kym_about': FieldConfig(
                description="The meme's about section on the Know Your Meme website.",
                format_template="Know Your Meme meme's about section: {}"
            ),
            'meme_image_description': FieldConfig(
                description="The visual description of the meme image.",
                format_template="Meme image description: {}"
            ),
            'meme_image_caption_style': FieldConfig(
                description="A description of the meme image's caption style.",
                format_template="Meme image caption style: {}"
            ),
        }
        self.text, self.image = self._parse_prompt(config, params, model, step)

    def get_text(self):
        print(self.text)
        return self.text

    def get_image(self):
        return self.image

    def _load_prompt_template(self, config, params, step):
        params['dynamic_section'] = self._build_dynamic_section(params)
        if step:
            text = config[self.class_name][step].format(**params)
        else:
            text = config[self.class_name].format(**params)
        return text, params

    def _parse_prompt(self, config: Dict, params: dict, model: str, step):
        text, params = self._load_prompt_template(config, params, step)
        if not params['meme_image']:
            return text, None
        if (model == 'gpt-4o' or model == 'claude-3.5-sonnet'
                or model == 'pixtral-large-2411'
                or model == 'llama-3.2-90b-vision-instruct'
                or model == 'qwen-2-vl-72b-instruct'
                or model == 'gemini-1.5-pro'):
            return text, params['meme_image']['url']
        # elif model == 'gemini-1.5-pro':
        #     meme_image_name = params['meme_image']['name']
        #     return text, meme_image_name
        elif model == 'qwq-32b-preview':
            return text, None

    @abstractmethod
    def _build_dynamic_section(self, params):
        pass


class ZeroShotPrompt(Prompt):

    def __init__(self, config: Dict, params: dict, model: str):
        super().__init__(config, params, model, None)

    def _build_dynamic_section(self, params):
        template_parts = []
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"# {config.description}")
                template_parts.append(config.format_template.format(value))
        return "\n    ".join(template_parts)


class FewShotPrompt(Prompt):

    def __init__(self, config: Dict, params: dict, model: str):
        self.meme_examples = _parse_meme_examples(params)
        super().__init__(config, params, model, None)

    def _build_dynamic_section(self, params):
        template_parts = []
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"\n# {config.description}")
                template_parts.append(config.format_template.format(value))

        template_parts.append("\nHere are some examples of how this meme template is typically used:\n")

        for i, example in enumerate(self.meme_examples, 1):
            template_parts.append(f"Example {i}:")
            for j, caption in enumerate(example, 1):
                template_parts.append(f"\tCaption {j}: {caption}")
            template_parts.append("")
        return "\n    ".join(template_parts)


class CotPrompt(Prompt):

    def __init__(self, config: Dict, params: dict, model: str):
        super().__init__(config, params, model, None)

    def _build_dynamic_section(self, params):
        template_parts = []
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"# {config.description}")
                template_parts.append(config.format_template.format(value))

        return "\n    ".join(template_parts)


class CovPrompt(Prompt):

    def __init__(self, config: Dict, params: dict, model: str, step, verification_context):
        self.verification_context = verification_context
        super().__init__(config, params, model, step)

    def _build_dynamic_section(self, params):
        template_parts = ["\nARTICLE AND MEME TEMPLATE INFORMATION:"]
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"# {config.description}")
                template_parts.append(config.format_template.format(value))

        for key, value in self.verification_context.items():
            if key == 'baseline':
                template_parts.append("\nINITIAL CAPTIONS:")
                for i, caption in enumerate(value, 1):
                    template_parts.append(f"Caption {i}: {caption}")
            if (key == 'plan_verification' and 'execute_verification'
                    not in self.verification_context):
                template_parts.append("\nVERIFICATION QUESTIONS:")
                for i, question in enumerate(value, 1):
                    template_parts.append(f"Question {i}: {question}")
            if key == 'execute_verification':
                template_parts.append("\nVERIFICATION QUESTIONS AND ANSWERS:")
                for i, answer in enumerate(value, 1):
                    template_parts.append(f"Question {i}: {self.verification_context['plan_verification'][i - 1]}")
                    template_parts.append(f"Answer {i}: {answer}")
        return "\n    ".join(template_parts)


class ClotPrompt(Prompt):

    def __init__(self, config: Dict, params: dict, model: str, step, context):
        self.context = context
        super().__init__(config, params, model, step)

    def _build_dynamic_section(self, params):
        template_parts = ["\nARTICLE AND MEME TEMPLATE INFORMATION:"]
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"# {config.description}")
                template_parts.append(config.format_template.format(value))

        for i, example in enumerate(self.context, 1):
            template_parts.append(f"Example {i}:")
            for j, caption in enumerate(example['captions'], 1):
                template_parts.append(f"Caption {j}: {caption}")
            template_parts.append(f"Reasoning: {example['reasoning']}")
        return "\n    ".join(template_parts)


class DebateEvaluatePrompt(Prompt):
    def __init__(self, config: Dict, params: dict, model: str):
        self.meme_examples = _parse_meme_examples(params)
        super().__init__(config, params, model, None)

    def _build_dynamic_section(self, params):
        template_parts = []
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"\n# {config.description}")
                template_parts.append(config.format_template.format(value))

        template_parts.append("\nHere are some examples of how this meme template is typically used:\n")

        for i, example in enumerate(self.meme_examples, 1):
            template_parts.append(f"Example {i}:")
            for j, caption in enumerate(example, 1):
                template_parts.append(f"\tCaption {j}: {caption}")
            template_parts.append("")
        return "\n    ".join(template_parts)


class DebateImprovedGenerationPrompt(Prompt):
    def __init__(self, config: Dict, params: dict, model: str):
        self.meme_examples = _parse_meme_examples(params)
        super().__init__(config, params, model, None)

    def _build_dynamic_section(self, params):
        template_parts = []
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"\n# {config.description}")
                template_parts.append(config.format_template.format(value))

        template_parts.append("\nHere are some examples of how this meme template is typically used:\n")

        for i, example in enumerate(self.meme_examples, 1):
            template_parts.append(f"Example {i}:")
            for j, caption in enumerate(example, 1):
                template_parts.append(f"\tCaption {j}: {caption}")
            template_parts.append("")
        return "\n    ".join(template_parts)


class DebateFinalEvaluatePrompt(Prompt):
    def __init__(self, config: Dict, params: dict, model: str):
        self.meme_examples = _parse_meme_examples(params)
        super().__init__(config, params, model, None)

    def _build_dynamic_section(self, params):
        template_parts = []
        for key, value in params.items():
            if key in self.field_config and key not in ['meme_image', 'fact_checker']:
                config = self.field_config[key]
                template_parts.append(f"\n# {config.description}")
                template_parts.append(config.format_template.format(value))

        template_parts.append("\nHere are some examples of how this meme template is typically used:\n")

        for i, example in enumerate(self.meme_examples, 1):
            template_parts.append(f"Example {i}:")
            for j, caption in enumerate(example, 1):
                template_parts.append(f"\tCaption {j}: {caption}")
            template_parts.append("")
        return "\n    ".join(template_parts)


class LlmJudgeStudyPrompt(Prompt):
    def __init__(self, config: Dict, params: dict, model: str):
        super().__init__(config, params, model, None)

    def _build_dynamic_section(self, params):
        pass
