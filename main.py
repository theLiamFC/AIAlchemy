from ai_alchemy import AIAlchemy
import asyncio
import sys
import json
import time
### AI Alchemist Assistant ID - this is NOT an API key
# SPIKE_ID = "asst_8WN5ksXpnNaBeAr1IKrLq4yd"
# WORKER_ID = "asst_gCp1YejKuc6X1progQ99C2fL"

default_messages = {
    "0": "Move forwards in a loop. There are motors in ports A and B",
    "1": "Move forward and backwards in order to maintin a distance of 100 using distance senor in port D and motors in ports A and B",
    "2": "Create a theramin using a touch sensor in port C and a distance sensor in port F",
    "3": "Print hello world to terminal: print('hello world')",
    "4": "Make a blue line following robot. There are motors in ports A and B and a color sensor in port C",
    "5": "Make roomba like robot that moves forwards until it hits something with the touch sensor \
and then it backs up, turns and moves forwards again. There are motors in ports A and B and a force senor in port F",
    "6": "I am placing the robot on a seesaw platform, balance at the center of the platform",
}

'''
# Main interface loop
async def interface_loop(ai_interface):
    intro_statement = "ChatGPT: What would you like to code today?\n"
    input_statement = (
        "['e','exit'] to stop the program.\n['help'] to see example prompts\n\nHuman: "
    )

    # Clear terminal screen
    for i in range(20):
        print("\n")
    user_prompt = input(intro_statement + input_statement)
    print()

    # Begin interface loop
    while True:
        if user_prompt.lower() == "help":
            print(str(json.dumps(default_messages, indent=4)) + "\n")
            user_prompt = input(input_statement)
            continue

        if user_prompt.lower() == "e" or user_prompt.lower() == "exit":
            print("Exiting the program...")
            return

        if user_prompt in default_messages:
            user_prompt = default_messages[user_prompt]
            print(f"Using default message: {user_prompt}\n")

        # Call ChatGPT with prompt
        result = await ai_interface.run_thread(user_prompt)
        print("ChatGPT: " + result)

        user_prompt = input(input_statement)
        print()
'''

async def run_assistant(ai_interface):
    result = await ai_interface.run()
    return result

async def check_mailbox(ai_interface):
    while True:
        print("checkingasdfgh: " + str(ai_interface.out_mail))
        if ai_interface.out_mail != None:
            print("ChatGPT: " + str(ai_interface.out_mail))
            print("entering input")
            ai_interface.out_mail = None
            ai_interface.in_mail = input("Human: ")
        else:
            await asyncio.sleep(0.5)    

if __name__ == "__main__":
    #### CHANGE SERIAL PORT HERE ####
    serial_port = "/dev/cu.usbmodem3356396133381"

    # Instantiate AIAlchemy Class
    task = default_messages["0"]
    device = "SPIKE"
    role = "ceo"
    ai_interface = AIAlchemy(role, task, device, serial_port, debug=False, verbose=False)

    # start loop
    fred = asyncio.new_event_loop()
    fred.create_task(check_mailbox(ai_interface))
    fred.create_task(run_assistant(ai_interface))
    fred.run_forever()
    
    # asyncio.run(check_mailbox(ai_interface))
    # asyncio.run(run_assistant(ai_interface))

    # task1 = asyncio.create_task(run_assistant(ai_interface))
    # task2 = asyncio.create_task(check_mailbox(ai_interface))

    # # Wait for both tasks to complete (this will effectively wait forever unless you break the loop within the tasks)
    # asyncio.gather(task1, task2)

    time.sleep(100)
    sys.exit()
    # Initiate Main Loop
    try:
        asyncio.run(interface_loop(ai_interface))
    except Exception as e:
        print("Main Loop Error: ", e)
    finally:
        ai_interface.close()
 