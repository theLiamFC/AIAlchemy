from openAIAlchemy import openAIAlchemy
import serial_interface
import asyncio
import sys

### ByteBard_XML ID
bb_id = "asst_CFsqmgnJhalDKnZvyjGKOtg7"
### PrimeBot ID
pb_id = "asst_merTUbrMxt0Fo1sc9P17G1Ax"
### Arduino Alvik ID
aa_id = "asst_NiIdeWySoj4RYIRU7t6r2mpG"
### Ai Alchemist ID
aa_id = "asst_8WN5ksXpnNaBeAr1IKrLq4yd"

### General test thread
# thread_id = "thread_UbU1hougFO6WE4kJCmK0ylRR"

# response = openAI_assistant.callChad(
#     bb_id, thread_id, "what is the weather in lexington MA"
# )


async def interface_loop(ai_interface, serial_interface):
    user_prompt = input(
        "What would you like your spike prime to do today?\n[Enter 'e' or 'exit' to stop the program.]\n"
    )
    if user_prompt == "":
        user_prompt = (
            "Write code to move the bot forward. There are motors in ports A and B"
        )
        print(f"Using defult message: {user_prompt}")
    while user_prompt.lower() != "e" and user_prompt.lower() != "exit":
        result = await ai_interface.run(user_prompt)
        print(result)
        # code, response = ai_interface.extract_code(result)
        # print(response)
        # repl_reply = serial_interface.serial_write(bytes(code, 'utf-8'))
        user_prompt = input("[Enter 'e' or 'exit' to stop the program.]\n")


# Run the main function in the event loop
if __name__ == "__main__":
    port_l = "/dev/cu.usbmodem3356396133381"
    port_j = "COM13"

    serial = serial_interface.serial_interface(port_j)
    # serial.test_serial()
    
    ai_interface = openAIAlchemy(aa_id, serial, debug=True, verbose=True)
    try:
        asyncio.run(interface_loop(ai_interface, serial))
    finally:
        ai_interface.close()