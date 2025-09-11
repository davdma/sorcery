"""Game state management for Sorcery."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Character(BaseModel):
    """Represents an NPC or character in the game."""
    name: str
    description: str = ""
    relationship: str = "neutral"
    knowledge: List[str] = Field(default_factory=list)
    first_met: Optional[datetime] = None


class Item(BaseModel):
    """Represents an item in the game."""
    name: str
    description: str = ""
    quantity: int = 1
    properties: Dict[str, Any] = Field(default_factory=dict)


class Location(BaseModel):
    """Represents a location in the game world."""
    name: str
    description: str = ""
    visited: bool = False
    first_visited: Optional[datetime] = None
    connections: List[str] = Field(default_factory=list)


class GameEvent(BaseModel):
    """Represents a significant event in the game."""
    timestamp: datetime
    description: str
    location: Optional[str] = None
    characters_involved: List[str] = Field(default_factory=list)
    items_involved: List[str] = Field(default_factory=list)


class PlayerStats(BaseModel):
    """Player statistics and attributes."""
    health: int = 100
    strength: int = 1
    wisdom: int = 1
    mana: int = 100
    charisma: int = 0
    gold: int = 0
    custom_stats: Dict[str, Any] = Field(default_factory=dict)


class GameState(BaseModel):
    """Complete game state."""
    
    # Game metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_saved: datetime = Field(default_factory=datetime.now)
    version: str = "0.1.0"
    
    # Player information
    player_name: str = "Adventurer"
    player_stats: PlayerStats = Field(default_factory=PlayerStats)
    
    # World state
    current_location: str = "starting_village"
    characters: Dict[str, Character] = Field(default_factory=dict)
    items: Dict[str, Item] = Field(default_factory=dict)
    locations: Dict[str, Location] = Field(default_factory=dict)
    
    # Game history
    events: List[GameEvent] = Field(default_factory=list)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    
    # Game settings
    difficulty: str = "normal"
    custom_flags: Dict[str, Any] = Field(default_factory=dict)
    
    def add_event(self, description: str, location: Optional[str] = None, 
                 characters: Optional[List[str]] = None, 
                 items: Optional[List[str]] = None) -> None:
        """Add an event to the game history."""
        event = GameEvent(
            timestamp=datetime.now(),
            description=description,
            location=location or self.current_location,
            characters_involved=characters or [],
            items_involved=items or []
        )
        self.events.append(event)
    
    def add_conversation(self, role: str, content: str) -> None:
        """Add a conversation turn to history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name."""
        return self.characters.get(name)
    
    def add_character(self, character: Character) -> None:
        """Add or update a character."""
        if character.first_met is None:
            character.first_met = datetime.now()
        self.characters[character.name] = character
    
    def get_item(self, name: str) -> Optional[Item]:
        """Get an item from inventory."""
        return self.items.get(name)
    
    def add_item(self, item: Item) -> None:
        """Add item to inventory."""
        existing = self.items.get(item.name)
        if existing:
            existing.quantity += item.quantity
        else:
            self.items[item.name] = item
    
    def remove_item(self, name: str, quantity: int = 1) -> bool:
        """Remove item from inventory. Returns True if successful."""
        item = self.items.get(name)
        if not item or item.quantity < quantity:
            return False
        
        item.quantity -= quantity
        if item.quantity <= 0:
            del self.items[name]
        return True
    
    def visit_location(self, location_name: str) -> None:
        """Mark a location as visited."""
        location = self.locations.get(location_name)
        if location:
            if not location.visited:
                location.visited = True
                location.first_visited = datetime.now()
        else:
            self.locations[location_name] = Location(
                name=location_name,
                visited=True,
                first_visited=datetime.now()
            )
        self.current_location = location_name
    
    def save_to_file(self, filepath: Path) -> None:
        """Save game state to JSON file."""
        self.last_saved = datetime.now()
        
        # Convert to dict and handle datetime serialization
        data = self.model_dump()
        
        # Custom JSON encoder for datetime objects
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=json_serializer)
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> 'GameState':
        """Load game state from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Convert datetime strings back to datetime objects
        def convert_datetime_fields(obj, fields):
            for field in fields:
                if field in obj and obj[field]:
                    try:
                        obj[field] = datetime.fromisoformat(obj[field])
                    except (ValueError, TypeError):
                        pass
        
        # Convert top-level datetime fields
        convert_datetime_fields(data, ['created_at', 'last_saved'])
        
        # Convert character datetime fields
        for char_data in data.get('characters', {}).values():
            convert_datetime_fields(char_data, ['first_met'])
        
        # Convert location datetime fields
        for loc_data in data.get('locations', {}).values():
            convert_datetime_fields(loc_data, ['first_visited'])
        
        # Convert event datetime fields
        for event_data in data.get('events', []):
            convert_datetime_fields(event_data, ['timestamp'])
        
        return cls(**data)
    
    def get_recent_events(self, limit: int = 10) -> List[GameEvent]:
        """Get the most recent events."""
        return self.events[-limit:] if self.events else []
    
    def get_inventory_summary(self) -> str:
        """Get a summary of the player's inventory."""
        if not self.items:
            return "Your inventory is empty."
        
        summary = "Inventory:\n"
        for item in self.items.values():
            quantity_str = f" (x{item.quantity})" if item.quantity > 1 else ""
            summary += f"- {item.name}{quantity_str}: {item.description}\n"
        
        return summary.strip()
    
    def get_stats_summary(self) -> str:
        """Get a summary of the player's stats."""
        stats = self.player_stats
        summary = f"Stats for {self.player_name}:\n"
        summary += f"Health: {stats.health}/100\n"
        summary += f"Strength: {stats.strength}/100\n"
        summary += f"Wisdom: {stats.strength}/100\n"
        summary += f"Mana: {stats.mana}/100\n"
        summary += f"Charisma: {stats.charisma}/100\n"
        summary += f"Gold: {stats.gold}\n"
        
        if stats.custom_stats:
            summary += "\nCustom Stats:\n"
            for key, value in stats.custom_stats.items():
                summary += f"{key}: {value}\n"
        
        return summary.strip()
