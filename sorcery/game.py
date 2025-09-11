"""Main game class for Sorcery."""

from pathlib import Path
from typing import Optional

from .config import Config
from .state import GameState
from .input_output import InputOutput
from .commands import CommandProcessor
from .llm import StoryTeller

class Game:
    """Main game controller for Sorcery."""
    
    def __init__(self, config: Config):
        self.config = config
        self.io = InputOutput(
            pretty=True,
            no_color=config.no_color,
            input_history_file=str(Path.home() / ".sorcery" / "input_history.txt")
        )
        
        # Initialize or load game state
        self.state = self._load_or_create_state()

        # Initialize LLM manager
        self.llm = StoryTeller(io=self.io, model=config.model)
        
        # Initialize command processor
        self.commands = CommandProcessor(self.state, self.io)
    
    def _load_or_create_state(self) -> GameState:
        """Load existing game state or create a new one."""
        if not self.config.new_game and self.config.save_file and self.config.save_file.exists():
            try:
                if self.config.debug:
                    print(f"Loading game from: {self.config.save_file}")
                return GameState.load_from_file(self.config.save_file)
            except Exception as e:
                if self.config.debug:
                    print(f"Failed to load save file: {e}")
                self.io.display_error(f"Failed to load save file: {e}")
                self.io.display_info("Starting new game instead.")
        
        # Create new game state
        state = GameState()
        
        # Initialize starting location
        state.visit_location("starting_village")
        if "starting_village" in state.locations:
            state.locations["starting_village"].description = (
                "A peaceful village at the edge of the wilderness, "
                "where your adventure begins."
            )
        
        return state
    
    def run(self) -> int:
        """Run the main game loop."""
        try:
            # Display welcome message
            self.io.display_welcome()
            
            # Check if LLM is available
            if not self.llm.get_available_model():
                self.io.display_error(
                    "No LLM model available. Please set up API keys properly:\n"
                    "- OPENAI_API_KEY for OpenAI models\n" 
                    "- ANTHROPIC_API_KEY for Anthropic models\n"
                    "- Or use --openai-api-key, --anthropic-api-key flag"
                )
                return 1
            
            # Show opening scene if new game
            if not self.state.conversation_history:
                opening_scene = self.llm.generate_opening_scene(self.state)
                self.io.display_scene(opening_scene)
            else:
                # Show a brief "resume" message
                self.io.display_info(
                    f"Welcome back, {self.state.player_name}! "
                    f"You are currently at: {self.state.current_location}",
                    "Game Resumed"
                )
            
            # Main game loop
            while True:
                try:
                    # Get user input
                    user_input = self.io.get_input()
                    
                    if not user_input:
                        continue
                    
                    # Check if it's a command
                    if self.commands.is_command(user_input):
                        handled, should_exit = self.commands.process_command(user_input)
                        if should_exit:
                            break
                        if handled:
                            continue
                    
                    # Process as game action
                    try:
                        scene_response = self.llm.generate_scene(user_input, self.state)
                        self.io.display_scene(scene_response)
                        
                    except Exception as e:
                        if self.config.debug:
                            raise
                        self.io.display_error(f"Failed to generate scene: {e}")
                
                except KeyboardInterrupt:
                    # Handle Ctrl+C gracefully
                    if self.io.confirm("\nSave before exiting?"):
                        self.commands.save_command([])
                    self.io.display_goodbye()
                    break
            
            return 0
            
        except Exception as e:
            if self.config.debug:
                raise
            self.io.display_error(f"Game error: {e}")
            return 1
