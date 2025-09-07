"""Input/Output handling for Sorcery CLI, based on aider's approach."""

import os
import sys
from typing import Optional, List, Dict, Any

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class SorceryCompleter(Completer):
    """Auto-completer for Sorcery commands."""
    
    def __init__(self):
        self.commands = [
            "/help", "/exit", "/quit", "/save", "/stats", 
            "/inventory", "/inv", "/look", "/map"
        ]
    
    def get_completions(self, document, complete_event):
        """Generate completions for the current input."""
        text = document.text_before_cursor
        
        if text.startswith('/'):
            for cmd in self.commands:
                if cmd.startswith(text.lower()):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=cmd,
                        display_meta=f"Command: {cmd}"
                    )


class InputOutput:
    """Handles input/output for the Sorcery CLI."""
    
    def __init__(
        self,
        pretty: bool = True,
        no_color: bool = False,
        input_history_file: Optional[str] = None,
    ):
        self.pretty = pretty and not no_color
        self.console = Console(color_system="truecolor" if self.pretty else None)
        
        # Initialize prompt session
        self.history = None
        if input_history_file:
            try:
                os.makedirs(os.path.dirname(input_history_file), exist_ok=True)
                self.history = FileHistory(input_history_file)
            except (OSError, PermissionError):
                pass
        
        # Setup prompt session
        self.prompt_session = PromptSession(
            history=self.history,
            completer=SorceryCompleter(),
            complete_while_typing=True,
            style=self._get_style(),
        )
        
        # Key bindings
        self.bindings = KeyBindings()
    
    def _get_style(self) -> Style:
        """Get the prompt toolkit style."""
        if not self.pretty:
            return Style()
        
        return Style.from_dict({
            'prompt': '#ansiblue bold',
            'input': '#ansiwhite',
            'completion-menu.completion': 'bg:#008888 #ffffff',
            'completion-menu.completion.current': 'bg:#00aaaa #000000',
            'scrollbar.background': 'bg:#88aaaa',
            'scrollbar.button': 'bg:#222222',
        })
    
    def display_welcome(self) -> None:
        """Display the welcome message."""
        if self.pretty:
            welcome_text = Text()
            welcome_text.append("🪄 Welcome to ", style="bold blue")
            welcome_text.append("SORCERY", style="bold magenta")
            welcome_text.append(" 🪄", style="bold blue")
            welcome_text.append("\nA CLI-based text adventure powered by LLMs\n", style="dim")
            
            panel = Panel(
                welcome_text,
                title="[bold green]Game Starting[/bold green]",
                border_style="blue",
                padding=(1, 2)
            )
            self.console.print(panel)
        else:
            self.console.print("=== SORCERY ===")
            self.console.print("A CLI-based text adventure powered by LLMs")
            self.console.print()
    
    def display_scene(self, content: str) -> None:
        """Display a game scene."""
        if self.pretty:
            panel = Panel(
                content,
                title="[bold cyan]Scene[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            )
            self.console.print(panel)
        else:
            self.console.print(f"\n--- Scene ---")
            self.console.print(content)
            self.console.print("-------------\n")
    
    def display_info(self, message: str, title: str = "Info") -> None:
        """Display an info message."""
        if self.pretty:
            panel = Panel(
                message,
                title=f"[bold blue]{title}[/bold blue]",
                border_style="blue",
                padding=(1, 2)
            )
            self.console.print(panel)
        else:
            self.console.print(f"\n--- {title} ---")
            self.console.print(message)
            self.console.print("-" * (len(title) + 8) + "\n")
    
    def display_error(self, message: str) -> None:
        """Display an error message."""
        if self.pretty:
            panel = Panel(
                message,
                title="[bold red]Error[/bold red]",
                border_style="red",
                padding=(1, 2)
            )
            self.console.print(panel)
        else:
            self.console.print(f"ERROR: {message}")
    
    def display_help(self) -> None:
        """Display help information."""
        help_text = """Available commands:

Game Commands:
  /help, /h          Show this help message
  /save              Save the current game
  /stats             Show player statistics  
  /inventory, /inv   Show inventory
  /look              Look around current location
  /map               Show visited locations
  /exit, /quit       Exit the game

During gameplay, simply type your actions in natural language.
The AI will respond with what happens next in your adventure!

Examples:
  > go north
  > talk to the merchant
  > pick up the sword
  > cast a fireball at the dragon
"""
        self.display_info(help_text, "Help")
    
    def get_input(self, prompt_text: str = "> ") -> str:
        """Get input from the user with the beautiful prompt box."""
        try:
            if self.pretty:
                # Create a styled prompt
                formatted_prompt = HTML(f'<prompt>{prompt_text}</prompt>')
                user_input = self.prompt_session.prompt(
                    formatted_prompt,
                    mouse_support=True,
                    wrap_lines=False,
                )
            else:
                user_input = self.prompt_session.prompt(prompt_text)
            
            return user_input.strip()
        
        except (KeyboardInterrupt, EOFError):
            return "/exit"
    
    def confirm(self, message: str) -> bool:
        """Ask for user confirmation."""
        try:
            response = self.prompt_session.prompt(f"{message} (y/N): ")
            return response.lower().startswith('y')
        except (KeyboardInterrupt, EOFError):
            return False
    
    def display_stats(self, stats_text: str) -> None:
        """Display player statistics."""
        self.display_info(stats_text, "Player Stats")
    
    def display_inventory(self, inventory_text: str) -> None:
        """Display player inventory."""
        self.display_info(inventory_text, "Inventory")
    
    def display_save_confirmation(self, filepath: str) -> None:
        """Display save confirmation."""
        if self.pretty:
            message = f"✅ Game saved successfully to:\n[dim]{filepath}[/dim]"
            panel = Panel(
                message,
                title="[bold green]Saved[/bold green]",
                border_style="green",
                padding=(1, 2)
            )
            self.console.print(panel)
        else:
            self.console.print(f"Game saved to: {filepath}")
    
    def display_goodbye(self) -> None:
        """Display goodbye message."""
        if self.pretty:
            goodbye_text = Text()
            goodbye_text.append("Thanks for playing ", style="bold blue")
            goodbye_text.append("SORCERY", style="bold magenta")
            goodbye_text.append("! 🌟", style="bold blue")
            goodbye_text.append("\nYour adventure awaits your return...", style="dim")
            
            panel = Panel(
                goodbye_text,
                title="[bold yellow]Farewell[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )
            self.console.print(panel)
        else:
            self.console.print("Thanks for playing SORCERY!")
            self.console.print("Your adventure awaits your return...")