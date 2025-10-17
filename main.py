import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = "https://models.github.ai/inference"
model = "microsoft/Phi-4-reasoning"
token = os.environ["GITHUB_TOKEN"]

client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token),
)

def generate_response(system_prompt: str, query:str):
    response = client.complete(
        messages=[
            SystemMessage(system_prompt),
            UserMessage(query),
        ],
        temperature=1.0,
        top_p=1.0,
        max_tokens=4000,
        model=model
    )

    return response.choices[0].message.content

# System Prompts
solver = open("system_prompts/solver.txt", "r")
evaluator = open("system_prompts/evaluator.txt", "r")
script_writer = open("system_prompts/script_writer.txt", "r")
video_generator = open("system_prompts/video_generator.txt", "r")

# Simple user interation
while True:
    query = input("query: ")
    if query.lower() in ["exit", "quit", "q"]:
        break

    answer = generate_response(solver, query)
    evaluation = generate_response(evaluator, answer)
    script = generate_response(script_writer, answer)
    video = generate_response(video_generator, script)

# Goal
# 1. LLM answers the question along with the proof
# 2. 2nd iteration to make sure the LLM is right and hasn't made any mistakes (Judge LLM)
# 3. Generate audio script explaining the answer
# 4. Generate python script according to the audio script
# 5. Split audio script into managable portions for the TTS model to generate the audio
# 6. Run the python script and get the videos
# 7. Align the audio and video together
# 8. Save the video