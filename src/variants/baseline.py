from meme_fact import MemeFact
from modules.module1_input import InputModule
from modules.module3_generation import BaselineGenerationModule


class BaselineVariant(MemeFact):

    def _run_impl(self, input_module: InputModule, **kwargs):
        generation_module = BaselineGenerationModule(input_module.get_ablation_input())

        return self._run_moderation_pipeline(generation_module=generation_module,
                                             num_memes=self.config['baseline']['num_memes'],
                                             enable_moderation=kwargs['moderate'])