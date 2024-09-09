import re
from dont_tell import OPENAI_API_KEY
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI
from openai.types.beta.threads import Text, TextDelta
from queue_handling import llm_response_queue, llm_response_condition

client = OpenAI(api_key=OPENAI_API_KEY)

class EventHandler(AssistantEventHandler):
    @override
    def on_text_delta(self, delta: TextDelta, snapshot: Text):
        content = delta.value
        llm_response_queue.put(content)
        # print("Added chunk content to the queue.")

thread = client.beta.threads.create()
thread_id = thread.id
# print(f"Created new thread with ID: {thread_id}")

def llm_model(user_input, assistant_id="asst_BPTPmSLF9eaaqyCkVZVCmK07"):
    try:
        # print(f"gpt thread ID: {thread_id}")
        event_handler = EventHandler()
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )
        streaming = True
        with llm_response_condition:
            llm_response_queue.put(streaming)
            # print("Added streaming mode indicator to the queue.")
            llm_response_condition.notify()
            # print("GPT Notified the consuming code.")
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            for event in stream:
                pass
        streaming = False
        llm_response_queue.put(streaming)
        # print("Added end of stream indicator to the queue.")
        streaming = True
        # print("llm_model completed successfully")
        return ""
    except Exception as e:
        print(f"Error occurred: {e}")
        raise e