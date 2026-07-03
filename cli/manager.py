from cli.prompt import InteractivePrompt
from cli.option import PromptOption
from util import run_command


class PromptManager:

    def __init__(self, prompt_stack : list[InteractivePrompt] = None):
        self._exit = False
        self.prompt_stack = prompt_stack if prompt_stack is not None else []

    def push_prompt(self, prompt: InteractivePrompt):
        self.prompt_stack.append(prompt)

    def pop_prompt(self):
        if self.prompt_stack:
            return self.prompt_stack.pop()
        return None

    def current_prompt(self):
        if self.prompt_stack:
            return self.prompt_stack[-1]
        return None
    
    def execute_option(self, option: PromptOption):
        # If option is another prompt, generate prompt
        # Else execute the action and return to the previous prompt   
        option_content = option.get_content()

        if isinstance(option_content, InteractivePrompt):
            self.push_prompt(option_content)
            return
        
        # Execute the action associated with the option
        run_command(option_content) 

        if option.should_exit():
            self._exit = True
            print("Exiting the prompt manager.")
            return
        
        if len(self.prompt_stack) > 1:
            self.pop_prompt()  

    def generate_prompts(self):
        prompt = self.current_prompt()

        if prompt is None:
            print("No prompts available.")
            self._exit = True
            return
        
        # Display the prompt message
        print(prompt.message)
        
        # Display the options
        for idx, option in enumerate(prompt.options, start=1):
            print(f"{idx}. {option.get_text()}")
        
        # Get user input
        user_choice = input("Select an option: ")
        
        try:
            choice_index = int(user_choice) - 1

            if choice_index == -1:
                self._exit = True
                print("Exiting the prompt manager.")
                return
            
            if 0 <= choice_index < len(prompt.options):
                selected_option = prompt.options[choice_index]
                self.execute_option(selected_option)
            else:
                print("Invalid option. Please try again.")
                return
        except ValueError:
            print("Invalid input. Please enter a number.")
            return

    def run(self):
        self._exit = False
        while not self._exit and self.prompt_stack:
            self.generate_prompts()