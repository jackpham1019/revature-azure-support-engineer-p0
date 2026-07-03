from cli.option import PromptOption

class InteractivePrompt:
    def __init__(self, message: str, options: list[PromptOption] = None):
        self.message = message
        self.options: list[PromptOption] = options if options is not None else []

    def add_option(self, option: PromptOption):
        self.options.append(option)
    
    def add_options(self, options: list[PromptOption]):
        self.options.extend(options)
    
    def replace_all_options(self, options: list[PromptOption]):
        self.options.clear()
        self.options.extend(options)
