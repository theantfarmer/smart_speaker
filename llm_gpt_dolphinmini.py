import ollama
import requests
import time
import subprocess
import threading 
from queue_handling import llm_response_queue, llm_response_condition

model_name = "gpt_dolphinmini"



def start_model_if_not_running(model_name=model_name):
    try:
        result = subprocess.run(["pgrep", "-f", model_name], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Model {model_name} is not running. Starting now...")
            subprocess.run(["ollama", "run", model_name], capture_output=True)
            print(f"{model_name} model started.")
            time.sleep(30)
        else:
            print(f"Model {model_name} is already running. No need to restart.")
    except Exception as e:
        print(f"Error: {e}")
        
threading.Thread(target=start_model_if_not_running).start()

def llm_model(command_text_stripped, model=model_name, timeout=60):
    formatted_message = [{"role": "user", "content": command_text_stripped}]
    streaming = True
    try:
        response = ollama.chat(
            model=model,
            messages=formatted_message,
            stream=streaming
        )
        with llm_response_condition:
            llm_response_queue.put(streaming)
            print("Added streaming mode indicator to the queue.")
            llm_response_condition.notify()
            print("Notified the consuming code.")
        for chunk in response:
            if chunk:
                if chunk.get('done', False):
                    print("End of stream reached.")
                    streaming = False
                    llm_response_queue.put(streaming) 
                    print("Added end of stream indicator to the queue.")
                    streaming = True
                    break
                message = chunk.get('message', {})
                content = message.get('content', '')
                llm_response_queue.put(content)
                print("Added chunk content to the queue.")
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        time.sleep(retry_interval)
        return "Failed to get a response from Ollama. Restarting model."
        threading.Thread(target=start_model_if_not_running).start()