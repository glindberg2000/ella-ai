import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import chainlit as cl

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with the API key
client = AsyncOpenAI(api_key=api_key)

# Settings for the OpenAI model
settings = {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 500,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}

@cl.on_chat_start
def start_chat():
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant."}],
    )

@cl.on_message
async def main(message: cl.Message):
    # Retrieve the message history from the user session
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message.content})

    # Initialize a Chainlit message object
    msg = cl.Message(content="")
    await msg.send()

    # Call the OpenAI API and stream the response
    stream = await client.chat.completions.create(
        messages=message_history, stream=True, **settings
    )

    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await msg.stream_token(token)

    # Update the message history with the assistant's response
    message_history.append({"role": "assistant", "content": msg.content})
    await msg.update()