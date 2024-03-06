import asyncio
from openai import AsyncOpenAI
import time

client = AsyncOpenAI()


async def createRunManager(client, thread_id, run_id):
    it = RunManager(client, thread_id, run_id)
    status = await it.start()
    return status


class RunManager:
    def __init__(self, client, thread_id, run_id):
        self.client = client
        self.thread_id = thread_id
        self.run_id = run_id
        self.exitStatus = "in_progress"

    async def start(self):
        queue = asyncio.Queue()

        # Create a list to keep track of tasks
        tasks = []

        # Start the status check loop
        status_task = asyncio.create_task(
            self.status_check(self.client, self.thread_id, self.run_id, queue)
        )
        tasks.append(status_task)

        # Start the response processing task
        process_task = asyncio.create_task(self.process_responses(queue, tasks))
        tasks.append(process_task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        return self.exitStatus

    async def status_check(self, client, thread_id, run_id, queue):
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

    async def process_responses(self, queue, tasks):
        non_final_statuses = ["queued", "in_progress"]
        while True:
            status = await queue.get()
            print(f"Received status: {status}")
            if status not in non_final_statuses:
                # Cancel all outstanding tasks
                for task in tasks:
                    task.cancel()
                print(f"Final status received: {status}. Proceeding to the next step.")
                self.exitStatus = status
                break


def api_timeout(tries=5, exp=2, start=1):
    def get_call(func):
        async def theCall(*args):
            for i in range(tries):
                begin = time.time()
                try:
                    return await asyncio.wait_for(
                        func(*args), timeout=((i + start) ** exp)
                    )
                except asyncio.TimeoutError as e:
                    print(e)
                finally:
                    end = time.time()
                    print("API Call Duration: ", end - begin)
            raise Exception("UnresponsiveAPI")

        return theCall

    return get_call


# Test function for timeout decorator
@api_timeout(tries=5, exp=1.5, start=1)
async def sleeperFunc(duration):
    await asyncio.sleep(duration)


# API: Get tool call
@api_timeout(tries=5, exp=2, start=1)
async def get_tool_call(client, thread_id, run_id):
    response = await client.beta.threads.runs.retrieve(
        thread_id=thread_id, run_id=run_id
    )
    return response.required_action


# API: Get run status
@api_timeout(tries=5, exp=2, start=1)
async def get_run_status(client, thread_id, run_id):
    response = await client.beta.threads.runs.retrieve(
        thread_id=thread_id, run_id=run_id
    )
    return response.status


# API: Get thread response
@api_timeout(tries=5, exp=2, start=1)
async def get_response(client, thread_id):
    response = await client.beta.threads.messages.list(thread_id)
    return response


# API: Get list of runs
@api_timeout(tries=5, exp=2, start=1)
async def get_runs(client, thread_id):
    runs = await client.beta.threads.runs.list(thread_id)
    return runs


# API: Get list of assistants
@api_timeout(tries=5, exp=2, start=1)
async def get_thread(client):
    my_assistants = await client.beta.assistants.list(
        order="desc",
        limit="20",
    )
    return my_assistants.data


# API: Kill all live runs
@api_timeout(tries=5, exp=2, start=1)
async def kill_all_runs(client, thread_id):
    live_states = ["queued", "in_progress", "requires_action"]
    runs = await client.beta.threads.runs.list(thread_id)
    for run in runs.data:
        if run.status in live_states:
            await client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)


async def main():
    try:
        # create the coroutine
        coro = get_thread(client)
        # create and execute the task
        task = asyncio.create_task(coro)
        value = await task
        print(value)
    except Exception as e:
        print(e)


asyncio.run(main())
