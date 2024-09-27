from meme_fact import MemeFact
from modules.module1_input import InputModule
from modules.module2_selection import SelectionModule
from modules.module3_generation import RAGGenerationModule


class RagVariant(MemeFact):

    def _run_impl(self, input_module: InputModule, **kwargs):

        selection_module = SelectionModule(input_module=input_module)
        generation_module = RAGGenerationModule(selection_module=selection_module)

        self._run_moderation_pipeline(generation_module=generation_module,
                                      num_memes=kwargs['rag']['num_memes'],
                                      enable_moderation=kwargs['enable_moderation'])
