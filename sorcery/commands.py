"""Command processing for Sorcery slash commands."""

from typing import Optional, Tuple, Dict, Callable
from pathlib import Path

from .state import GameState
from .input_output import InputOutput


class CommandProcessor:
    """Processes slash commands in the Sorcery game."""
    
    def __init__(self, game_state: GameState, io: InputOutput):
        self.state = game_state
        self.io = io
        
        # Map commands to their handler functions
        self.commands: Dict[str, Callable] = {
            'help': self.help_command,
            'h': self.help_command,
            'save': self.save_command,
            'stats': self.stats_command,
            'inventory': self.inventory_command,
            'inv': self.inventory_command,
            'look': self.look_command,
            'map': self.map_command,
            'exit': self.exit_command,
            'quit': self.exit_command,
        }
    
    def is_command(self, user_input: str) -> bool:
        """Check if the input is a slash command."""
        return user_input.startswith('/')
    
    def process_command(self, user_input: str) -> Tuple[bool, bool]:
        """
        Process a slash command.
        
        Returns:
            Tuple[bool, bool]: (command_handled, should_exit)
        """
        if not self.is_command(user_input):
            return False, False
        
        # Parse command and arguments
        parts = user_input[1:].split()  # Remove leading '/' and split
        if not parts:
            self.io.display_error("Empty command. Type /help for available commands.")
            return True, False
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Execute command
        if command in self.commands:
            try:
                return self.commands[command](args)
            except Exception as e:
                self.io.display_error(f"Error executing command '{command}': {e}")
                return True, False
        else:
            self.io.display_error(f"Unknown command: /{command}. Type /help for available commands.")
            return True, False
    
    def help_command(self, args: list) -> Tuple[bool, bool]:
        """Display help information."""
        self.io.display_help()
        return True, False
    
    def save_command(self, args: list) -> Tuple[bool, bool]:
        """Save the game."""
        try:
            # Use custom filename if provided
            if args:
                save_path = Path(args[0])
                if not save_path.suffix:
                    save_path = save_path.with_suffix('.json')
            else:
                # Use default save location from config
                save_path = Path.home() / ".sorcery" / "save.json"
            
            self.state.save_to_file(save_path)
            self.io.display_save_confirmation(str(save_path))
            
        except Exception as e:
            self.io.display_error(f"Failed to save game: {e}")
        
        return True, False
    
    def stats_command(self, args: list) -> Tuple[bool, bool]:
        """Display player statistics."""
        stats_text = self.state.get_stats_summary()
        self.io.display_stats(stats_text)
        return True, False
    
    def inventory_command(self, args: list) -> Tuple[bool, bool]:
        """Display player inventory."""
        inventory_text = self.state.get_inventory_summary()
        self.io.display_inventory(inventory_text)
        return True, False
    
    def look_command(self, args: list) -> Tuple[bool, bool]:
        """Look around the current location."""
        current_location = self.state.locations.get(self.state.current_location)
        if current_location:
            location_text = f"Location: {current_location.name}\n"
            location_text += f"Description: {current_location.description}\n"
            
            if current_location.connections:
                location_text += f"Exits: {', '.join(current_location.connections)}\n"
            
            # Add nearby characters
            nearby_chars = [
                char for char in self.state.characters.values()
                if hasattr(char, 'current_location') and 
                char.current_location == self.state.current_location  # type: ignore
            ]
            
            if nearby_chars:
                location_text += "Characters present: " + ", ".join(char.name for char in nearby_chars)
            
            self.io.display_info(location_text, "Current Location")
        else:
            self.io.display_info(f"You are at: {self.state.current_location}", "Current Location")
        
        return True, False
    
    def map_command(self, args: list) -> Tuple[bool, bool]:
        """Show visited locations."""
        if not self.state.locations:
            self.io.display_info("No locations visited yet.", "Map")
            return True, False
        
        visited_locations = [
            loc for loc in self.state.locations.values() if loc.visited
        ]
        
        if not visited_locations:
            self.io.display_info("No locations visited yet.", "Map")
            return True, False
        
        map_text = "Visited Locations:\n\n"
        for location in visited_locations:
            marker = " <- Current" if location.name == self.state.current_location else ""
            map_text += f"📍 {location.name}{marker}\n"
            if location.description:
                map_text += f"   {location.description}\n"
            if location.first_visited:
                map_text += f"   First visited: {location.first_visited.strftime('%Y-%m-%d %H:%M')}\n"
            map_text += "\n"
        
        self.io.display_info(map_text.strip(), "Map")
        return True, False
    
    def exit_command(self, args: list) -> Tuple[bool, bool]:
        """Exit the game."""
        # Prompt for save before exiting
        if self.io.confirm("Save before exiting?"):
            self.save_command([])
        
        self.io.display_goodbye()
        return True, True