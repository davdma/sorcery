# Sorcery!

One of my favorite games growing up was a fantasy story book game on the phone called `Sorcery!`. It's a classic choose your own adventure RPG where you interact with the world through choices, and those choices entirely shape how the story unfolds. Even with the pre-written storyline, the world felt so expansive and big that I still felt limitless within its bounds. I was so hooked that I played through the entire series spanning four separate apps (to the detriment of my dad's credit card).

With the powerful abilities of LLMs, I thought how fun would it be to have a interactive story RPG where the story teller was an LLM that generates the next scene on the fly, and a world where nothing is pre-determined and anything could possibly happen? This is the motivation behind why I sought to recreate the ultimate `Sorcery!` experience. I wanted to give it the power of being infinitely large and replayable, with each world being completely unique based on choices and prompts.

## Specifications

I wanted to build the entire game as a CLI program similar to the CLI AI-assistant tools. I wanted to build an interface similar to claude code or aider, where you interact with the game (or underlying LLM) through a pretty prompt box with backslash commands `/save`, `/exit` or `/help`. It also provides stats and basic inventory in the terminal window (`/stats` or `/inventory` for detailed output). 

## Design

One of the core design choices going into building this game was keeping a clear separation of game state and LLM narration. The narration should be based off of clear discrete game states, not the LLM's internal state which is prone to error. As the game progresses, the LLM bases its outputs off of the saved information on player stats, inventory, character history, and places, so that it cannot deviate too far from the current storyline. The game engine serves as a mediator between the LLM and the game state, as well as the LLM and the player inputs:

```text
LLM <-> program <-> state

LLM <-> program <-> player
```

The LLMs main function is to take the game state and generate the next narrative scene. At the end of the scene, the LLM must give options to the player in a strict choice format. The only scenario in which players are allowed to freely write prompts is in dialogue mode with an NPC - anything that the player types in the prompt will be interpreted as speech towards the NPC in the context of the game. After a choice has been made, the LLM generates the next scene from the selection and updates the game state. All this is done in the program by parsing the LLM output in a deterministic way (a standardized communication mode is agreed upon between program and LLM to allow for easy parsing).

A foundational rule is **the LLM should only generate narrative content, not dictate core game rules**. The LLM should still be constrained by the resources given to the player, e.g. stats like `strength` or `charisma`, so players cannot easily cheat and break immersion by giving themselves imaginary powers or items.

## Game States

Saved game states involve information about characters encountered (e.g. what we know about them, relationship status etc.). Here are a list of possible context objects to save:

- Characters encountered
- Items acquired (inventory)
- Locations visited
- Actions taken
- Past events

The context can be saved in JSON for persistent state.

## System Prompts

To control the LLM outputs, a strong set of system prompts are given to instruct it on how to interact with the program.

```text
You are the narrator of a text-based adventure game. You never invent items or characters that are not in the game state.
Only describe what the player sees or minor flavor text. Always follow instructions in the structured game state.
```

To avoid hitting token limits, only provide in context a fixed length buffer of previous actions/events, but provide the model with the ability to search for past info if needed for consistency.

