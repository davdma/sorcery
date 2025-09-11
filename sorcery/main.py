#!/usr/bin/env python3
"""Main entry point for Sorcery CLI game."""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional

from .game import Game
from .config import Config


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for Sorcery CLI."""
    parser = argparse.ArgumentParser(
        prog="sorcery",
        description="CLI-based text adventure game powered by LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model to use (default: gpt-4o-mini)",
    )
    
    parser.add_argument(
        "--openai-api-key",
        help="Specify the OpenAI API key",
    )

    parser.add_argument(
        "--anthropic-api-key",
        help="Specify the Anthropic API key"
    )
    
    parser.add_argument(
        "--save-file",
        type=Path,
        help="Path to save file (default: ~/.sorcery/save.json)",
    )
    
    parser.add_argument(
        "--new-game",
        action="store_true",
        help="Start a new game (ignores existing save)",
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    
    return parser


def main(args: Optional[list] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    try:
        # Load configuration
        config = Config(
            model=parsed_args.model,
            openai_api_key=parsed_args.openai_api_key,
            anthropic_api_key=parsed_args.anthropic_api_key,
            save_file=parsed_args.save_file,
            new_game=parsed_args.new_game,
            debug=parsed_args.debug,
            no_color=parsed_args.no_color,
        )

        if parsed_args.openai_api_key:
            os.environ["OPENAI_API_KEY"] = parsed_args.openai_api_key
        
        if parsed_args.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = parsed_args.anthropic_api_key
        
        # Initialize and start game
        game = Game(config)
        return game.run()
        
    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
        return 1
    except Exception as e:
        if parsed_args.debug:
            raise
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
