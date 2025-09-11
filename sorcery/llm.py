"""LLM integration for Sorcery game."""
import litellm
import os
import threading
import time
import traceback
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from litellm.litellm_core_utils.prompt_templates.factory import get_system_prompt
from .history import StorySummary
from .input_output import InputOutput
from .state import GameState
from .chat_chunks import ChatChunks

RETRY_TIMEOUT = 60
request_timeout = 600

DEFAULT_MODEL_NAME = "gpt-4o"

# Mapping of model aliases to their canonical names
MODEL_ALIASES = {
    # Claude models
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-3-5-haiku-20241022",
    "opus": "claude-opus-4-20250514",
    # GPT models
    "4": "gpt-4-0613",
    "4o": "gpt-4o",
    "4-turbo": "gpt-4-1106-preview",
    "35turbo": "gpt-3.5-turbo",
    "35-turbo": "gpt-3.5-turbo",
    "3": "gpt-3.5-turbo",
    # Other models
    # "deepseek": "deepseek/deepseek-chat",
    # "flash": "gemini/gemini-2.5-flash",
    # "flash-lite": "gemini/gemini-2.5-flash-lite",
    # "quasar": "openrouter/openrouter/quasar-alpha",
    # "r1": "deepseek/deepseek-reasoner",
    # "gemini-2.5-pro": "gemini/gemini-2.5-pro",
    # "gemini": "gemini/gemini-2.5-pro",
    # "gemini-exp": "gemini/gemini-2.5-pro-exp-03-25",
    # "grok3": "xai/grok-3-beta",
    # "optimus": "openrouter/openrouter/optimus-alpha",
}

OPENAI_MODELS = """
o1
o1-preview
o1-mini
o3-mini
gpt-4
gpt-4o
gpt-4o-2024-05-13
gpt-4-turbo-preview
gpt-4-0314
gpt-4-0613
gpt-4-32k
gpt-4-32k-0314
gpt-4-32k-0613
gpt-4-turbo
gpt-4-turbo-2024-04-09
gpt-4-1106-preview
gpt-4-0125-preview
gpt-4-vision-preview
gpt-4-1106-vision-preview
gpt-4o-mini
gpt-4o-mini-2024-07-18
gpt-3.5-turbo
gpt-3.5-turbo-0301
gpt-3.5-turbo-0613
gpt-3.5-turbo-1106
gpt-3.5-turbo-0125
gpt-3.5-turbo-16k
gpt-3.5-turbo-16k-0613
"""

OPENAI_MODELS = [ln.strip() for ln in OPENAI_MODELS.splitlines() if ln.strip()]

ANTHROPIC_MODELS = """
claude-2
claude-2.1
claude-3-haiku-20240307
claude-3-5-haiku-20241022
claude-3-opus-20240229
claude-3-sonnet-20240229
claude-3-5-sonnet-20240620
claude-3-5-sonnet-20241022
claude-sonnet-4-20250514
claude-opus-4-20250514
"""

ANTHROPIC_MODELS = [ln.strip() for ln in ANTHROPIC_MODELS.splitlines() if ln.strip()]

def get_model_info(model) -> Dict[str, str]:
    """Helper function to fetch max tokens, max input and output tokens
    from openrouter."""
    if model in OPENAI_MODELS:
        url_part = 'openai/' + model
    elif model in ANTHROPIC_MODELS:
        url_part = 'anthropic/' + model
    else:
        raise ValueError('Model not recognized')

    url = "https://openrouter.ai/" + url_part
    try:
        import requests
        response = requests.get(url, timeout=5, verify=True)
        if response.status_code != 200:
            return {}
        html = response.text
        import re

        if re.search(
            rf"The model\s*.*{re.escape(url_part)}.* is not available", html, re.IGNORECASE
        ):
            print(f"\033[91mError: Model '{url_part}' is not available\033[0m")
            return {}
        text = re.sub(r"<[^>]+>", " ", html)
        context_match = re.search(r"([\d,]+)\s*context", text)
        if context_match:
            context_str = context_match.group(1).replace(",", "")
            context_size = int(context_str)
        else:
            context_size = None
        input_cost_match = re.search(r"\$\s*([\d.]+)\s*/M input tokens", text, re.IGNORECASE)
        output_cost_match = re.search(r"\$\s*([\d.]+)\s*/M output tokens", text, re.IGNORECASE)
        input_cost = float(input_cost_match.group(1)) / 1000000 if input_cost_match else None
        output_cost = float(output_cost_match.group(1)) / 1000000 if output_cost_match else None
        if context_size is None or input_cost is None or output_cost is None:
            return {}
        params = {
            "max_input_tokens": context_size,
            "max_tokens": context_size,
            "max_output_tokens": context_size,
            "input_cost_per_token": input_cost,
            "output_cost_per_token": output_cost,
        }
        return params
    except Exception as e:
        print("Error fetching openrouter info:", str(e))
        return {}

def _build_system_prompt(game_state: GameState) -> str:
    """Build the system prompt with game context."""
    return f"""You are the narrator of SORCERY, a text-based RPG adventure game.

Current Game Context:
- Player: {game_state.player_name}
- Location: {game_state.current_location}

{game_state.get_stats_summary()}

Recent Events: {[event.description for event in game_state.get_recent_events(3)]}

Inventory: {list(game_state.items.keys()) if game_state.items else "Empty"}

Instructions:
1. Generate vivid, immersive narrative responses to player actions
2. Maintain consistency with the game state, plot, and previous narrative scenes 
3. Present choices and consequences clearly
4. Keep responses between 100-300 words
5. Use second person ("You see...", "You hear...")
6. Make the world feel alive and reactive
7. Respect the player's stats and inventory limitations
8. Don't break character or reference being an AI

The player will describe their action, and you should respond with what happens next in the story. The scene you write should flow naturally from the previous scene, as if the story simply flipped to the next page. Focus on consistency: for example, if the character in the last scene was holding a sword, he/she should not suddenly be holding a bow in the following scene. Same goes with descriptions of the environment or characters unless introducing information not previously established."""

class Model():
    def __init__(self, model_name):
        # map alias to canonical model name
        model_name = MODEL_ALIASES.get(model_name, model_name)
        if not self.validate_model_name(model_name):
            model_name = DEFAULT_MODEL_NAME
        self.name = model_name
        self.max_chat_history_tokens = 1024
        self.info = get_model_info(model_name)
        
        max_input_tokens = self.info.get("max_input_tokens") or 0
        # min 1k max 8k tokens
        self.max_chat_history_tokens = min(max(max_input_tokens / 16, 1024), 8192)
        self.api_key = self.validate_environment()
        if self.api_key is None:
            raise ValueError("No API key found in environment.")

    def validate_model_name(self, model_name):
        if model_name not in OPENAI_MODELS and model_name not in ANTHROPIC_MODELS:
            return False
        return True

    def validate_environment(self):
        """Validate and fetch API key in environment."""
        var = None
        if self.name and self.name in OPENAI_MODELS:
            var = "OPENAI_API_KEY"
        elif self.name and self.name in ANTHROPIC_MODELS:
            var = "ANTHROPIC_API_KEY"

        if var and os.environ.get(var):
            return var
        else:
            return None

    def tokenizer(self, text):
        return litellm.encode(model=self.name, text=text)

    def token_count(self, messages):
        if type(messages) is list:
            try:
                return litellm.token_counter(model=self.name, messages=messages)
            except Exception as err:
                print(f"Unable to count token: {err}")
                return 0
        
        if type(messages) is str:
            msgs = messages
            try:
                return len(self.tokenizer(msgs))
            except Exception as err:
                print(f"Unable to count tokens: {err}")
                return 0
        else:
            raise ValueError(f"Unexpected type for messages: {type(messages)}")

    def send_completion(self, messages, stream, temperature=None):
        """Note: can explore having streaming instead one shot generated response
        for better experience."""
        kwargs = dict(
            model=self.name,
            stream=stream,
            messages=messages,
            timeout=request_timeout
        )

        return litellm.completion(**kwargs)

    def simple_send_with_retries(self, messages):
        from .exceptions import LiteLLMExceptions

        litellm_ex = LiteLLMExceptions()
        retry_delay = 0.125

        while True:
            try:
                kwargs = {
                    "messages": messages,
                    "stream": False,
                }
                response = self.send_completion(**kwargs)
                if not response or not hasattr(response, "choices") or not response.choices:
                    return None
                res = response.choices[0].message.content
            except litellm_ex.exceptions_tuple() as err:
                ex_info = litellm_ex.get_ex_info(err)
                print(str(err))
                if ex_info.description:
                    print(ex_info.description)
                should_retry = ex_info.retry
                if should_retry:
                    retry_delay *= 2
                    if retry_delay > RETRY_TIMEOUT:
                        should_retry = False
                if not should_retry:
                    return None
                print(f"Retrying in {retry_delay:.1f} seconds...")
                time.sleep(retry_delay)
                continue
            except AttributeError:
                return None


class StoryTeller:
    """Manages LLMs and handles scene generation."""
    
    def __init__(self, io: InputOutput, model: str = "gpt-4o-mini"):
        # IO
        self.io = io

        # Initialize model
        self.model = Model(model)
        
        # Initialize summarizer
        self.summarizer = StorySummary(model=self.model)
        self.summarizer_thread = None

        # Separation of message types
        self.system_message = []
        self.done_messages = []
        self.cur_messages = []

    def get_available_model(self) -> Optional[Model]:
        """Get the model if it has api key set and openrouter info fetched."""
        if not self.model.api_key or not self.model.info:
            return None
        return self.model

    def set_system_prompt(self, state: GameState):
        """Update the system prompt based on the game state."""
        self.system_message = [
            dict(role="system", content=_build_system_prompt(state))
        ]

    def summarize_start(self):
        """Start summarizing process on past messages."""
        if not self.summarizer.too_big(self.done_messages):
            return

        self.summarize_end()

        # start summarizing
        self.summarizer_thread = threading.Thread(target=self.summarize_worker)
        self.summarizer_thread.start()

    def summarize_worker(self):
        # make copy of list of messages to summarize
        self.summarizing_messages = list(self.done_messages)
        try:
            self.summarized_done_messages = self.summarizer.summarize(self.summarizing_messages)
        except ValueError as err:
            self.io.display_error(err.args[0])

    def summarize_end(self):
        if self.summarizer_thread is None:
            return

        self.summarizer_thread.join()
        self.summarizer_thread = None

        # if new user messages added to history, discard summary
        if self.summarizing_messages == self.done_messages:
            self.done_messages = self.summarized_done_messages

        self.summarizing_messages = None
        self.summarized_done_messages = []

    def move_back_cur_messages(self):
        self.done_messages += self.cur_messages
        self.summarize_start()
        self.cur_messages = []
    
    def format_messages(self):
        """Combine chunks of messages for sending."""
        chunks = ChatChunks()
        chunks.system = self.system_message

        # summarizer call
        self.summarize_end()
        chunks.past_scenes = self.done_messages
        chunks.cur = list(self.cur_messages)
        chunks.reminder = []

        return chunks

    def send_message(self, inp):
        """Send message to the model for response.

        TODO: figure out what to do with keyboard interrupts"""
        self.cur_messages += [
            dict(role="user", content=inp)
        ]

        chunks = self.format_messages()
        messages = chunks.all_messages()

        # check if fits in token limits
        if not self.check_tokens(messages):
            return ""

        from .exceptions import LiteLLMExceptions
        litellm_ex = LiteLLMExceptions()
        retry_delay = 0.125
        exhausted = False

        while True:
            try:
                res = self.model.send_completion(messages, False)
                if not res or not hasattr(res, "choices") or not res.choices:
                    return ""
                return res.choices[0].message.content
            except litellm_ex.exceptions_tuple() as err:
                print(err)
                ex_info = litellm_ex.get_ex_info(err)

                if ex_info.name == "ContextWindowExceededError":
                    exhausted = True
                    break

                should_retry = ex_info.retry
                if should_retry:
                    retry_delay *= 2
                    if retry_delay > RETRY_TIMEOUT:
                        should_retry = False

                if not should_retry:
                    break

                err_msg = str(err)
                if ex_info.description:
                    self.io.display_error(err_msg)
                    self.io.display_error(ex_info.description)
                else:
                    self.io.display_error(err_msg)

                self.io.display_info(f"Retrying in {retry_delay:.1f} seconds...")
                time.sleep(retry_delay)
                continue
            except Exception as err:
                lines = traceback.format_exception(type(err), err, err.__traceback__)
                self.io.display_error("".join(lines))
                self.io.display_error(str(err))
                return ""


    def check_tokens(self, messages):
        """Check if messages fit inside token limits."""
        input_tokens = self.model.token_count(messages)
        max_input_tokens = self.model.info.get("max_input_tokens") or 0

        if max_input_tokens and input_tokens >= max_input_tokens:
            self.io.display_error(f"Your estimated chat context of {input_tokens:,} tokens exceeds the"
                                  f" {max_input_tokens:,} token limit for {self.model.name}!")
            if not self.io.confirm("Try to proceed anyways?"):
                return False
        return True

    def generate_scene(self, user_action: str, game_state: GameState) -> str:
        """Generate a scene response to the user's action."""
        self.set_system_prompt(game_state)
        # Build the prompt with user action
        prompt = f"Player action: {user_action}"
        
        # Generate the scene
        scene_content = self.send_message(prompt)

        self.move_back_cur_messages()

        # add reply to cur messages
        self.cur_messages += [
            dict(role="assistant", content=scene_content)
        ]

        # Add to conversation history
        game_state.add_conversation("user", user_action)
        game_state.add_conversation("assistant", scene_content)
        
        # Add event to game history
        game_state.add_event(f"Player: {user_action}")
        
        return scene_content
    
    def generate_opening_scene(self, game_state: GameState) -> str:
        """Generate the opening scene of the game."""
        self.set_system_prompt(game_state)
        opening_prompt = (
            "As the narrator, generate an opening scene for a new adventure. "
            "Set the scene in a fantasy world and give the player "
            "their first choice of action. Make it engaging and immersive."
        )
        
        scene_content = self.send_message(opening_prompt)

        self.move_back_cur_messages()

        # add reply to cur messages
        self.cur_messages += [
            dict(role="assistant", content=scene_content)
        ]
        
        # Add to conversation history
        game_state.add_conversation("system", "Game started")
        game_state.add_conversation("assistant", scene_content)
        
        # Add opening event
        game_state.add_event("Adventure begins")
        
        return scene_content
