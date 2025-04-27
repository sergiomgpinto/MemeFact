from meme_fact import MemeFact
from modules.module1_input import InputModule
from modules.module3_generation import BaselineGenerationModule


class BaselineVariant(MemeFact):

    def __init__(self, config):
        super().__init__(config)

    def _run_impl(self, input_module: InputModule, **kwargs):
        generation_module = BaselineGenerationModule(ablation_input=input_module.get_ablation_input(),
                                                     params=kwargs['model_params'],
                                                     parse=kwargs['parse'])
        return self._run_moderation_pipeline(generation_module=generation_module,
                                             enable_moderation=kwargs['moderate'],
                                             num_memes=self.config[self.class_name]['num_memes']
                                             if not kwargs['bot'] else kwargs['num_memes'],
                                             model=kwargs['model'],
                                             prompt_type=self.config[self.class_name]['prompt_type'])
