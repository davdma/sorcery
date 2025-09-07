"""LLM integration for Sorcery game."""

import os
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .state import GameState


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_scene(self, prompt: str, game_state: GameState) -> str:
        """Generate a scene description based on the prompt and game state."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (has required dependencies and API key)."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if self.api_key and OPENAI_AVAILABLE:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def is_available(self) -> bool:
        """Check if OpenAI provider is available."""
        return OPENAI_AVAILABLE and self.api_key is not None and self.client is not None
    
    def generate_scene(self, prompt: str, game_state: GameState) -> str:
        """Generate scene using OpenAI API."""
        if not self.is_available():
            raise RuntimeError("OpenAI provider is not available")
        
        system_prompt = self._build_system_prompt(game_state)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.8,
            )
            
            return response.choices[0].message.content or "The scene unfolds mysteriously..."
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate scene with OpenAI: {e}")
    
    def _build_system_prompt(self, game_state: GameState) -> str:
        """Build the system prompt with game context."""
        return f"""You are the narrator of SORCERY, a text-based RPG adventure game.

Current Game Context:
- Player: {game_state.player_name}
- Location: {game_state.current_location}
- Health: {game_state.player_stats.health}/100
- Level: {game_state.player_stats.level}
- Gold: {game_state.player_stats.gold}

Recent Events: {[event.description for event in game_state.get_recent_events(3)]}

Inventory: {list(game_state.items.keys()) if game_state.items else "Empty"}

Instructions:
1. Generate vivid, immersive narrative responses to player actions
2. Maintain consistency with the game state and previous events  
3. Present choices and consequences clearly
4. Keep responses between 100-300 words
5. Use second person ("You see...", "You hear...")
6. Make the world feel alive and reactive
7. Respect the player's stats and inventory limitations
8. Don't break character or reference being an AI

The player will describe their action, and you should respond with what happens next in the story."""


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, model: str = "claude-3-haiku-20240307", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Anthropic provider is available."""
        return ANTHROPIC_AVAILABLE and self.api_key is not None and self.client is not None
    
    def generate_scene(self, prompt: str, game_state: GameState) -> str:
        """Generate scene using Anthropic API."""
        if not self.is_available():
            raise RuntimeError("Anthropic provider is not available")
        
        system_prompt = self._build_system_prompt(game_state)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.8,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text if response.content else "The scene unfolds mysteriously..."
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate scene with Anthropic: {e}")
    
    def _build_system_prompt(self, game_state: GameState) -> str:
        """Build the system prompt with game context."""
        return f"""You are the narrator of SORCERY, a text-based RPG adventure game.

Current Game Context:
- Player: {game_state.player_name}
- Location: {game_state.current_location}
- Health: {game_state.player_stats.health}/100
- Level: {game_state.player_stats.level}
- Gold: {game_state.player_stats.gold}

Recent Events: {[event.description for event in game_state.get_recent_events(3)]}

Inventory: {list(game_state.items.keys()) if game_state.items else "Empty"}

Instructions:
1. Generate vivid, immersive narrative responses to player actions
2. Maintain consistency with the game state and previous events  
3. Present choices and consequences clearly
4. Keep responses between 100-300 words
5. Use second person ("You see...", "You hear...")
6. Make the world feel alive and reactive
7. Respect the player's stats and inventory limitations
8. Don't break character or reference being an AI

The player will describe their action, and you should respond with what happens next in the story."""


class LLMManager:
    """Manages LLM providers and handles scene generation."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.providers: List[LLMProvider] = []
        
        # Initialize providers based on model preference
        if model.startswith("gpt") or model.startswith("openai"):
            self.providers.extend([
                OpenAIProvider(model, api_key),
                AnthropicProvider(api_key=api_key),
            ])
        elif model.startswith("claude") or model.startswith("anthropic"):
            self.providers.extend([
                AnthropicProvider(model, api_key),
                OpenAIProvider(api_key=api_key),
            ])
        else:
            # Default order
            self.providers.extend([
                OpenAIProvider(model, api_key),
                AnthropicProvider(api_key=api_key),
            ])
    
    def get_available_provider(self) -> Optional[LLMProvider]:
        """Get the first available LLM provider."""
        for provider in self.providers:
            if provider.is_available():
                return provider
        return None
    
    def generate_scene(self, user_action: str, game_state: GameState) -> str:
        """Generate a scene response to the user's action."""
        provider = self.get_available_provider()
        if not provider:
            raise RuntimeError(
                "No LLM providers available. Please check your API keys:\n"
                "- Set OPENAI_API_KEY for OpenAI GPT models\n"
                "- Set ANTHROPIC_API_KEY for Anthropic Claude models\n"
                "- Or use --api-key flag when starting the game"
            )
        
        # Build the prompt with user action
        prompt = f"Player action: {user_action}"
        
        # Generate the scene
        scene_content = provider.generate_scene(prompt, game_state)
        
        # Add to conversation history
        game_state.add_conversation("user", user_action)
        game_state.add_conversation("assistant", scene_content)
        
        # Add event to game history
        game_state.add_event(f"Player: {user_action}")
        
        return scene_content
    
    def generate_opening_scene(self, game_state: GameState) -> str:
        """Generate the opening scene of the game."""
        opening_prompt = (
            "Generate an opening scene for a new adventure. "
            "Set the scene in a fantasy world and give the player "
            "their first choice of action. Make it engaging and immersive."
        )
        
        provider = self.get_available_provider()
        if not provider:
            return (
                "Welcome, adventurer! You find yourself at the edge of a mysterious forest, "
                "with paths leading in multiple directions. The sun is setting, and you must "
                "choose your next move carefully. What do you do?"
            )
        
        scene_content = provider.generate_scene(opening_prompt, game_state)
        
        # Add to conversation history
        game_state.add_conversation("system", "Game started")
        game_state.add_conversation("assistant", scene_content)
        
        # Add opening event
        game_state.add_event("Adventure begins")
        
        return scene_content