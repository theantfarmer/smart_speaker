from dont_tell import OPENAI_API_KEY
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI
from openai.types.beta.threads import Text, TextDelta
import re

client = OpenAI(api_key=OPENAI_API_KEY)

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.collected_messages = []
        self.return_text = ""

    @override
    def on_text_delta(self, delta: TextDelta, snapshot: Text):
        text = delta.value
        self.collected_messages.append(text)
        self.check_and_return_text()

    def check_and_return_text(self):
        collected_text = ''.join(self.collected_messages)
        match = re.search(r'[.!?]\s+|\n', collected_text)
        if match:
            end_index = match.end()
            self.return_text = collected_text[:end_index].strip()
            self.collected_messages = [collected_text[end_index:]]
        else:
            self.return_text = ""

    def get_return_text(self):
        return_text = self.return_text
        self.return_text = ""
        return return_text

    def done(self):
        if self.collected_messages:
            self.return_text = ''.join(self.collected_messages).strip()
        self.collected_messages = []

thread = client.beta.threads.create()
thread_id = thread.id
print(f"Created new thread with ID: {thread_id}")

def llm_model(user_input, assistant_id="asst_BPTPmSLF9eaaqyCkVZVCmK07"):
    try:
        print(f"gpt thread ID: {thread_id}")
        event_handler = EventHandler()
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )

        full_return_text = ""
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            for event in stream:
                return_text = event_handler.get_return_text()
                print(f"Return text in stream: {return_text}")
                if return_text:
                    full_return_text += return_text

        event_handler.done()
        return_text = event_handler.get_return_text()
        if return_text:
            full_return_text += return_text

        print("llm_model completed successfully")
        return full_return_text

    except Exception as e:
        print(f"Error occurred: {e}")
        raise e