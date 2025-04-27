from meme_fact import MemeFact
from modules.module1_input import InputModule
from modules.module2_selection import SelectionModule
from modules.module3_generation import RAGGenerationModule


class RagVariant(MemeFact):

    def _run_impl(self, input_module: InputModule, **kwargs):
        selection_module = SelectionModule(input_module=input_module)
        generation_module = RAGGenerationModule(selection_module=selection_module,
                                                ablation_input=input_module.get_ablation_input(),
                                                params=kwargs['model_params'],
                                                parse=kwargs['parse'])

        return self._run_moderation_pipeline(generation_module=generation_module,
                                             num_memes=self.config[self.class_name]['num_memes']
                                             if not kwargs['bot'] else kwargs['num_memes'],
                                             model=kwargs['model'],
                                             prompt_type=self.config[self.class_name]['prompt_type'],
                                             enable_moderation=kwargs['moderate'])
