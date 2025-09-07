# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sorcery is a CLI-based text adventure game powered by LLMs. It recreates the classic "choose your own adventure" RPG experience where an LLM generates narrative content dynamically, creating an infinitely replayable world where each playthrough is unique.

## Architecture

The game follows a clear separation between game state and LLM narration:

```
LLM <-> program <-> state
LLM <-> program <-> player
```

Key principles:
- **State-driven narrative**: The LLM generates content based on discrete game states (player stats, inventory, character history, locations) rather than its own internal state
- **Deterministic parsing**: Communication between the LLM and program uses a standardized format for reliable parsing
- **Constrained generation**: The LLM only generates narrative content and must respect game rules and player resources

## Game State Management

The game persists state in JSON format containing:
- Characters encountered (relationships, knowledge)
- Items acquired (inventory)
- Locations visited
- Actions taken
- Past events

## Current Status

This is an early-stage project with design specifications documented in `design.md`. The codebase currently contains only documentation and design files - no implementation has been started yet.

## Development Notes

- The game will be built as a CLI program similar to claude-code or aider
- Interface will include a prompt box with slash commands (`/save`, `/exit`, `/help`, `/stats`, `/inventory`)
- System prompts will constrain LLM behavior to prevent rule-breaking or inconsistent narrative generation
- Token management will use a fixed-length buffer of recent events with search capabilities for historical consistency