"""Configuration management for Sorcery."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration for Sorcery game."""
    
    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    api_key: Optional[str] = Field(default=None, description="API key for LLM service")
    save_file: Optional[Path] = Field(default=None, description="Path to save file")
    new_game: bool = Field(default=False, description="Start a new game")
    debug: bool = Field(default=False, description="Enable debug mode")
    no_color: bool = Field(default=False, description="Disable colored output")
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Set default save file location
        if self.save_file is None:
            sorcery_dir = Path.home() / ".sorcery"
            sorcery_dir.mkdir(exist_ok=True)
            self.save_file = sorcery_dir / "save.json"
        
        # Get API key from environment if not provided
        if self.api_key is None:
            self.api_key = (
                os.getenv("OPENAI_API_KEY") or
                os.getenv("ANTHROPIC_API_KEY") or
                os.getenv("SORCERY_API_KEY")
            )
        
        # Validate API key
        if not self.api_key:
            raise ValueError(
                "No API key provided. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, "
                "or SORCERY_API_KEY environment variable, or use --api-key flag."
            )