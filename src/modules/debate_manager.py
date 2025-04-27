import yaml


def _parse_evaluation_feedback(raw_feedback: str) -> dict:
    try:
        parsed_yaml = yaml.safe_load(raw_feedback)

        # Initialize our feedback structure
        feedback = {
            'generator1': {
                'scores': {},
                'strengths': [],
                'improvements': []
            },
            'generator2': {
                'scores': {},
                'strengths': [],
                'improvements': []
            },
            'synthesis': []
        }

        # Extract data from the parsed YAML
        yaml_data = parsed_yaml.get('output', {})

        # Process generator 1
        if 'generator_1' in yaml_data:
            gen1_data = yaml_data['generator_1']
            # Parse scores (converting from "X/5" format to integer)
            for criterion, score in gen1_data.get('scores', {}).items():
                score_value = int(str(score).split('/')[0])
                feedback['generator1']['scores'][criterion] = score_value
            # Parse lists
            feedback['generator1']['strengths'] = gen1_data.get('strengths', [])
            feedback['generator1']['improvements'] = gen1_data.get('improvements', [])

        # Process generator 2
        if 'generator_2' in yaml_data:
            gen2_data = yaml_data['generator_2']
            # Parse scores
            for criterion, score in gen2_data.get('scores', {}).items():
                score_value = int(str(score).split('/')[0])
                feedback['generator2']['scores'][criterion] = score_value
            # Parse lists
            feedback['generator2']['strengths'] = gen2_data.get('strengths', [])
            feedback['generator2']['improvements'] = gen2_data.get('improvements', [])

        # Process synthesis
        if 'synthesis' in yaml_data:
            feedback['synthesis'] = yaml_data['synthesis'].get('combinations', [])

        return feedback
    except Exception as e:
        raise Exception(f"Failed to parse evaluation feedback: {str(e)}")


def _format_feedback_for_generator(feedback_dict):

    # Create a YAML structure for better readability
    feedback_data = {
        'output': {
            'evaluation': {
                'scores': {
                    k.title(): f"{v}/5" for k, v in feedback_dict['scores'].items()
                },
                'strengths': feedback_dict['strengths'],
                'improvements': feedback_dict['improvements']
            }
        }
    }

    # Convert to YAML string
    yaml_str = yaml.dump(feedback_data, sort_keys=False, allow_unicode=True)

    # Add a friendly header
    return "Here's the evaluation of your previous captions:\n\n" + yaml_str


def _extract_improved_captions(improved_output):
    try:
        # Parse the YAML content
        parsed_yaml = yaml.safe_load(improved_output)

        # Extract captions from the YAML structure
        captions_dict = parsed_yaml.get('output', {}).get('captions', {})

        # Convert to list of formatted strings
        formatted_captions = []
        for caption_num, caption_text in sorted(captions_dict.items()):
            # Remove any extra quotes
            clean_text = str(caption_text).strip('"\'')
            formatted_captions.append(f"Caption {caption_num}: {clean_text}")

        # Join with newlines
        return '\n'.join(formatted_captions)

    except Exception as e:
        raise Exception(f"Failed to extract improved captions: {str(e)}")


def _parse_final_evaluation(raw_evaluation: str) -> dict:
    try:
        # Initialize the result structure with default values
        result = {
            'generator1': {
                'scores': {},
                'average': 0.0
            },
            'generator2': {
                'scores': {},
                'average': 0.0
            },
            'winner': {
                'generator': '',  # New field to store which generator won
                'captions': [],  # Will store the list of winning captions
                'confidence': 0,  # New field to store confidence percentage
                'explanation': ''
            }
        }

        # Parse the YAML content
        parsed_yaml = yaml.safe_load(raw_evaluation)

        # Validate root structure
        if not parsed_yaml or 'output' not in parsed_yaml:
            raise ValueError("Missing 'output' root node in YAML")

        yaml_data = parsed_yaml['output']

        # Process Generator 1's scores and average
        if 'generator_1' in yaml_data:
            gen1_data = yaml_data['generator_1']
            # Process scores, converting from "X/5" format to float
            for criterion, score in gen1_data.get('scores', {}).items():
                score_value = float(str(score).split('/')[0])
                result['generator1']['scores'][criterion] = score_value
            # Process average score
            if 'average' in gen1_data:
                result['generator1']['average'] = float(
                    str(gen1_data['average']).split('/')[0]
                )

        # Process Generator 2's scores and average (same logic as Generator 1)
        if 'generator_2' in yaml_data:
            gen2_data = yaml_data['generator_2']
            for criterion, score in gen2_data.get('scores', {}).items():
                score_value = float(str(score).split('/')[0])
                result['generator2']['scores'][criterion] = score_value
            if 'average' in gen2_data:
                result['generator2']['average'] = float(
                    str(gen2_data['average']).split('/')[0]
                )

        # Process the decision section containing winner information
        if 'decision' in yaml_data:
            decision_data = yaml_data['decision']

            # Store which generator won
            result['winner']['generator'] = decision_data.get('winning_generator', '').strip('"\'')

            # Process confidence percentage (remove % symbol and convert to float)
            confidence = decision_data.get('confidence', '0%')
            result['winner']['confidence'] = float(str(confidence).rstrip('%'))

            # Process winning captions list
            winning_captions = decision_data.get('winning_captions', [])
            # Ensure we have a list of strings with cleaned values
            result['winner']['captions'] = [
                str(caption).strip('"\'') for caption in winning_captions
            ] if winning_captions else []

            # Process explanation
            explanation = decision_data.get('explanation', '')
            result['winner']['explanation'] = str(explanation).strip('"\'')

        return result

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format: {e}")
    except Exception as e:
        raise ValueError(f"Failed to parse final evaluation: {str(e)}")


class DebateManager:
    def __init__(self, generators, evaluators, model_manager):
        self.generator1 = generators[0]
        self.generator2 = generators[1]
        self.evaluator = evaluators[0]
        self.model_manager = model_manager

    def run_debate(self, params):
        # Round 1: Initial generation
        #print(params)
        captions1 = self.model_manager.inference_model(self.generator1, 'few-shot', params, mode='creative')
        captions2 = self.model_manager.inference_model(self.generator2, 'few-shot', params, mode='creative')
        print(f'captions1 round1: {captions1}')
        print(f'captions2 round1: {captions2}')

        # Round 2: Evaluation and feedback
        evaluator_params = params.copy()
        evaluator_params.update({
            'captions1': captions1,
            'captions2': captions2,
        })
        raw_feedback = self.model_manager.inference_model(
            self.evaluator,
            'debate-evaluate',
            evaluator_params,
            mode='deterministic')

        print(f'raw feedback round: {raw_feedback}')
        feedback = _parse_evaluation_feedback(raw_feedback)
        print(f'feedback parsed: {feedback}')

        # Round 3: Improved generation with feedback
        generator_params = params.copy()
        generator_params.update({
            'previous_captions': captions1,
            'feedback': _format_feedback_for_generator(feedback['generator1'])
        })

        improved_captions1 = self.model_manager.inference_model(
            self.generator1,
            'debate-improved-generation',
            generator_params,
            mode='creative')
        print(f'improved_captions1 round3: {improved_captions1}')

        generator_params = params.copy()
        generator_params.update({
            'previous_captions': captions2,
            'feedback': _format_feedback_for_generator(feedback['generator1'])
        })

        improved_captions2 = self.model_manager.inference_model(
            self.generator2,
            'debate-improved-generation',
            generator_params,
            mode='creative')
        print(f'improved_captions2 round3: {improved_captions2}')

        # Final evaluation - prepare parameters for final judgment
        final_evaluator_params = params.copy()
        final_evaluator_params.update({
            'improved_captions1': _extract_improved_captions(improved_captions1),
            'improved_captions2': _extract_improved_captions(improved_captions2),
        })

        # Get final evaluation and selection
        raw_final_result = self.model_manager.inference_model(
            self.evaluator,
            'debate-final-evaluate',
            final_evaluator_params,
            mode='deterministic')
        print(f'raw final result round4: {raw_final_result}')
        final_result = _parse_final_evaluation(raw_final_result)
        print(f'final result round4 parsed: {final_result}')
        print(f'winner captions: {final_result['winner']['captions']}')
        return final_result['winner']['captions']
