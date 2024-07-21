import chainlit as cl
import asyncio

@cl.on_chat_start
async def start():
    await cl.Message("Welcome! Send any message to see the process in action.").send()

@cl.on_message
async def main(message: cl.Message):
    # Create a main message for the entire process
    main_msg = cl.Message(content="")
    await main_msg.send()

    # Simulate a process with main steps and sub-steps
    main_steps = ["Thinking", "Processing", "Finalizing"]
    for i, main_step in enumerate(main_steps, 1):
        # Update the main message with a collapsible section for each main step
        await main_msg.stream_token(f"\n<details><summary>{i}. {main_step}</summary>\n\n")
        
        sub_steps = ["Analyze", "Compute", "Summarize"]
        for j, sub_step in enumerate(sub_steps, 1):
            # Stream sub-step content
            await main_msg.stream_token(f"{i}.{j} {sub_step}: ")
            for k in range(2):
                await main_msg.stream_token(f"Part {k+1}... ")
                await asyncio.sleep(0.3)
            await main_msg.stream_token("Completed!\n")
            await asyncio.sleep(0.5)
        
        # Close the collapsible section
        await main_msg.stream_token("\n</details>")

    # Add a final summary
    await main_msg.stream_token("\n\n**Process completed successfully!**")

    # Update the final message
    await main_msg.update()

    # Send a completion message
    await cl.Message("All steps completed. You can expand each section to see details.").send()

if __name__ == "__main__":
    cl.run()