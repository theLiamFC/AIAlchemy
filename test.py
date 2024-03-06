### ByteBard_XML ID
bb_id = "asst_CFsqmgnJhalDKnZvyjGKOtg7"
### PrimeBot ID
pb_id = "asst_merTUbrMxt0Fo1sc9P17G1Ax"
### Ai Alchemist ID
aa_id = "asst_8WN5ksXpnNaBeAr1IKrLq4yd"

### General test thread
thread_id = "thread_UbU1hougFO6WE4kJCmK0ylRR"

import asyncio
import os
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


async def status_check(thread_id, run_id, queue):
    while True:
        try:
            # Fetch the status of the assistant run
            assistant_run = await client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )
            status = assistant_run.status
            await queue.put(status)  # Put the status into the queue for processing
        except Exception as e:
            print(f"An error occurred while fetching the status: {e}")

        await asyncio.sleep(1)  # Wait for 1 second before the next status check


async def process_responses(queue, tasks):
    non_final_statuses = ["queued", "in_progress", "requires_action"]
    while True:
        status = await queue.get()
        print(f"Received status: {status}")
        if status not in non_final_statuses:
            # Cancel all outstanding tasks
            for task in tasks:
                task.cancel()
            print(f"Final status received: {status}. Proceeding to the next step.")
            break


async def main():
    thread_id = "your_thread_id_here"
    run_id = "your_run_id_here"
    queue = asyncio.Queue()

    # Create a list to keep track of tasks
    tasks = []

    # Start the status check loop
    status_task = asyncio.create_task(status_check(thread_id, run_id, queue))
    tasks.append(status_task)

    # Start the response processing task
    process_task = asyncio.create_task(process_responses(queue, tasks))
    tasks.append(process_task)

    # Wait for all tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)


asyncio.run(main())
