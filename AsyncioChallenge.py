import asyncio
import time
import random

mailbox = False
start = time.perf_counter()
counter = 0

async def monitor_mailbox():
    global mailbox
    global counter

    if mailbox:
        print("MONITOR: got the mailbox at: ",str(time.perf_counter() - start))
        mailbox = False
        counter += 1
    else:
        rand = random.randint(1, 3)
        print("MONITOR: waiting ",str(rand)," at ", str(time.perf_counter() - start))
        await asyncio.sleep(rand)

async def mailman():
    global mailbox

    # if counter > 5:
    #     print("Stop loop")
    #     loop.stop()

    if random.randint(0,10) > 5 and not mailbox:
        mailbox = True
        print("MAILMAN: put something in the mailbox at ",str(time.perf_counter() - start))
    else:
        rand = random.randint(3, 5)
        print("MAILMAN: waiting ", str(rand), " at ", str(time.perf_counter() - start))
        await asyncio.sleep(rand)

# CHALLENGE:
# How do we run monitor mailbox and mailmain in a loop so that
# when one of them finishes it immediately starts again.