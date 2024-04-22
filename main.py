from ai_alchemy import AIAlchemy
from serial_interface import SerialInterface
import asyncio
import sys
import json

### AI Alchemist Assistant ID - this is NOT an API key
assitant_id = "asst_8WN5ksXpnNaBeAr1IKrLq4yd"

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


# Main interface loop
async def interface_loop(ai_interface):
    use_cam = False
    additional_instructions = ""
    yes_cam = "Use the get_visual_feedback function to confirm what the robot is doing"
    no_cam  = "Don't use the get_visul_feedback, just use get_feedback"
    additional_instructions += yes_cam if use_cam else no_cam
    intro_statement = "ChatGPT: What would you like your spike prime to do today?\n"
    input_statement = (
        "['e','exit'] to stop the program.\n['help'] to see example prompts\n\nHuman: "
    )

    # Reset terminal screen
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
        result = await ai_interface.run(user_prompt + additional_instructions)
        print("ChatGPT: " + result)

        user_prompt = input(input_statement)
        print()


# Run the main function in the event loop
if __name__ == "__main__":
    #### CHANGE SERIAL PORT HERE ####
    # port = "/dev/cu.usbmodem3356396133381"
    port = "COM13"

    # Instantiate Serial Interface
    try:
        serial = SerialInterface(port, fake_serial=True)
    except Exception as e:
        print("Serial Connection Error: ", e)
        sys.exit()

    # Instantiate AIAlchemy Class
    ai_interface = AIAlchemy(assitant_id, serial, debug=False, verbose=False)

    # Initiate Main Loop
    try:
        asyncio.run(interface_loop(ai_interface))
    except Exception as e:
        print("Main Loop Error: ", e)
    finally:
        ai_interface.close()
