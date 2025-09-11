from dataclasses import dataclass, field
from typing import List

@dataclass
class ChatChunks:
    system: List = field(default_factory=list)
    examples: List = field(default_factory=list)
    past_scenes: List = field(default_factory=list)
    cur: List = field(default_factory=list)
    reminder: List = field(default_factory=list)

    def all_messages(self):
        return (self.system
                + self.examples
                + self.past_scenes
                + self.cur
                + self.reminder
        )

