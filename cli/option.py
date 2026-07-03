from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.prompt import InteractivePrompt

class PromptOption:
    def __init__(self, option_text: str, content: list[str] | InteractivePrompt, exit_after: bool = False):
        self._option_text = option_text
        self._content = content
        self._exit_after = exit_after

    def get_text(self):
        return self._option_text
    
    def get_content(self):
        return self._content

    def should_exit(self):
        return self._exit_after