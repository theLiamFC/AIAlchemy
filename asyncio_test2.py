import asyncio
import time
import random

LIMIT = 5
mailbox = None
start = time.perf_counter()
counter = 0

print("Starting...")

async def monitor_mailbox():
    global mailbox
    global counter

    while True:

        if mailbox != None:
            print(f"MONITOR: got the mailbox at: {time.perf_counter() - start:.2f}")
            print(f"Mailbox message: {mailbox}, Counter: {counter}")
            mailbox = None
            counter += 1

            if counter > LIMIT:  # Optional: stopping condition
                print(f"Counter reached {LIMIT}, MONITOR stopping...")
                break
        else:
            rand = random.randint(1, 3)
            print(f"MONITOR: waiting {rand} seconds at {time.perf_counter() - start:.2f}")
            await asyncio.sleep(rand)

async def mailman():
    global mailbox

    while True:
        # if counter > LIMIT:  # Optional: stopping condition
        #     print("Counter reached 5, MAILMAN stopping...")
        #     break
        if random.randint(0, 10) > 3 and mailbox == None:
            mailbox = input("A message for the mailbox: ")
            print(f"MAILMAN: put something in the mailbox at {time.perf_counter() - start:.2f}")
            print(f"Mailbox status: {mailbox}, Counter: {counter}")
        else:
            rand = random.randint(3, 5)
            print(f"MAILMAN: waiting {rand} seconds at {time.perf_counter() - start:.2f}")
            await asyncio.sleep(rand)

async def main():
    task1 = asyncio.create_task(monitor_mailbox())
    task2 = asyncio.create_task(mailman())

    # Wait for both tasks to complete (this will effectively wait forever unless you break the loop within the tasks)
    await asyncio.gather(task1,task2)

# Run the main function using asyncio.run if this is the main module
if __name__ == "__main__":
    asyncio.run(main())
