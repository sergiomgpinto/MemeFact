from meme_fact import MemeFact
from modules.module1_input import InputModule
from modules.module2_selection import SelectionModule
from modules.module3_generation import DebateGenerationModule


class RlhfVariant(MemeFact):

    def _run_impl(self, input_module: InputModule, **kwargs):

        selection_module = SelectionModule(input_module=input_module)
        generation_module = DebateGenerationModule(selection_module=selection_module)

        self._run_moderation_pipeline(generation_module=generation_module,
                                      num_memes=kwargs['rlhf']['num_memes'],
                                      enable_moderation=kwargs['baseline']['enable_moderation'])
