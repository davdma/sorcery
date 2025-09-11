from sorcery import prompts

class StorySummary:
    def __init__(self, model=None, max_tokens=1024):
        if not model:
            raise ValueError("At least one model must be provided.")
        self.model = model
        self.max_tokens = max_tokens
        self.token_count = self.model.token_count

    def too_big(self, messages):
        sized = self.tokenize(messages)
        total = sum(tokens for tokens, _msg in sized)
        return total > self.max_tokens

    def tokenize(self, messages):
        sized = []
        for msg in messages:
            tokens = self.token_count([msg])
            sized.append((tokens, msg))
        return sized

    def summarize(self, messages, depth=0):
        if not self.model:
            raise ValueError("No models available for summarization")

        sized = self.tokenize(messages)
        total = sum(tokens for tokens, _ in sized)
        if total <= self.max_tokens and depth == 0:
            return messages
        
        min_split = 4
        if len(messages) <= min_split or depth > 3:
            return self.summarize_all(messages)

        tail_tokens = 0
        split_index = len(messages)
        half_max_tokens = self.max_tokens // 2

        # Iterate over the messages in reverse order
        for i in range(len(sized) - 1, -1, -1):
            tokens, _msg = sized[i]
            if tail_tokens + tokens < half_max_tokens:
                tail_tokens += tokens
                split_index = i
            else:
                break

        # Ensure the head ends with a scene followed by user response
        while messages[split_index - 1]["role"] != "user" and split_index > 1:
            split_index -= 1

        if split_index <= min_split:
            return self.summarize_all(messages)

        # Split head and tail
        tail = messages[split_index:]

        # Only size the head once
        sized_head = sized[:split_index]

        # Precompute token limit (fallback to 4096 if undefined)
        model_max_input_tokens = self.model.info.get("max_input_tokens") or 4096
        model_max_input_tokens -= 512  # reserve buffer for safety

        keep = []
        total = 0

        # Iterate in original order, summing tokens until limit
        for tokens, msg in sized_head:
            total += tokens
            if total > model_max_input_tokens:
                break
            keep.append(msg)
        # No need to reverse lists back and forth

        summary = self.summarize_all(keep)

        # If the combined summary and tail still fits, return directly
        summary_tokens = self.token_count(summary)
        tail_tokens = sum(tokens for tokens, _ in sized[split_index:])
        if summary_tokens + tail_tokens < self.max_tokens:
            return summary + tail

        # Otherwise recurse with increased depth
        return self.summarize(summary + tail, depth + 1)

    def summarize_all(self, messages):
        content = ""
        for msg in messages:
            role = msg["role"].upper()
            if role not in ("USER", "ASSISTANT"):
                continue
            if role == "USER":
                content += "# Player\n"
            else:
                content += "# Narrator\n"
            content += msg["content"]
            if not content.endswith("\n"):
                content += "\n"

        summarize_messages = [
            dict(role="system", content=prompts.summarize),
            dict(role="user", content=content),
        ]

        try:
            summary = self.model.simple_send_with_retries(summarize_messages)
            if summary is not None:
                return [dict(role="user", content=summary)]
        except Exception as e:
            print(f"Summarization failed for model {self.model.name}: {str(e)}")

        raise ValueError("summarizer unexpectedly failed for all models")
