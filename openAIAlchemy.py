from openai import OpenAI
import cv2 as cv
import time
import asyncio
import json
import sys
import base64

### private variables
# assistant_id
# thread_id
# client_id
# run_id
# queryDict

### ACTION ITEMS ### NOW IN NOTION
# - ALWAYS: expand json file with more SPIKE syntax
# - ALWAYS: improve commenting and readability
#
# - TODO: !!! handle errors and hanging api calls
# - TODO: !!! Clean up text output and make more presentable
# - TODO: tailor assistant instructions to get better function calling behavior
# - TODO: create functionality for a debug log exported as txt file
#
# - BUG: json.decoder.JSONDecodeError: Invalid \escape: line 2 column 41 (char 42)
#        occurs in __function_manager() on line 174
# - BUG: freezing after "Run in Progress" and "Submitting tool outputs"
#        seems to be an issue on the openAI end
#        search file for "FREEZING" to find occurances
# - BUG: chatGPT indentaton does not mesh well with REPL
#        might be best to always parse the response and delete all spaces after new line if possible
# - BUG: code does not seem to be properly uploaded to SPIKE when running on Liam's Mac
#


class openAIAlchemy:
    def __init__(
        self, assistant_id, serial, thread_id=None, debug=False, verbose=False
    ):
        self.client = OpenAI()
        # self.kill_all_runs()  #  causes errors
        self.assistant_id = assistant_id
        self.serial_interface = serial
        self.debug = debug
        self.verbose = verbose
        self.run_id = None
        self.queryDict = json.load(open("queryDict.json", "r"))
        self.cam = cv.VideoCapture(0)
        self.this_log = open("this_log.txt", "w")  # write over this file
        self.all_log = open("all_log.txt", "a")  # append to this files

        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        self.log_print(f"\n\n\nPROGRAM OUTPUT FROM {formatted_time}\n")

        if thread_id == None:
            newThread = self.client.beta.threads.create()
            self.thread_id = newThread.id
            self.debug_print(f"THREAD_ID: {self.thread_id}")
        else:
            self.thread_id = thread_id

    # Public Function
    # Change model of current assistant
    # "gpt-4", gpt
    def change_model(self, modelNum):
        models = ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo-0125"]
        self.client.beta.assistants.update(
            self.assistant_id,
            model=models[modelNum],
        )

    # Public Debugging Function
    # Retreive assistants for purpose of finding IDs
    def get_assistants(self):
        my_assistants = self.client.beta.assistants.list(
            order="desc",
            limit="20",
        )
        return my_assistants.data

    # Public Debugging Function
    # Retrieve all runs in a current thread
    def get_runs(self):
        runs = self.client.beta.threads.runs.list(self.thread_id)
        return runs

    # Public Debugging Function
    # Kills all runs that are in progress or requiring action
    def kill_all_runs(self):
        runs = self.get_runs()
        for run in runs.data:
            if run.status == "in_progress" or run.status == "requires_action":
                self.client.beta.threads.runs.cancel(
                    thread_id=self.thread_id, run_id=run.id
                )

    # Public Debugging Function
    # Add message to current thread
    def add_message(self, message):
        self.debug_print("Adding message")
        self.client.beta.threads.messages.create(
            self.thread_id,
            role="user",
            content=message,
        )

    # Public Debugging Function
    # Get most recent message from the thread
    def get_message(self):
        messages = self.client.beta.threads.messages.list(self.thread_id)
        return messages.data[0].content[0].text.value

    # Start and or manage run of current thread
    async def __run_manager(self):
        if self.run_id == None:  # check for existing run
            self.debug_print("Creating new run")
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread_id, assistant_id=self.assistant_id
            )  # BUG FREEZING HERE
            self.run_id = run.id
        else:
            self.debug_print("Using existing run")
        self.debug_print("Run in progress")
        status = "in_progress"

        # entering status monitoring loop
        # exits upon completion, failure, or tool call response required
        last_time = time.time()
        while status not in ["completed", "failed", "requires_action"]:
            status = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id, run_id=self.run_id
            ).status  # BUG this api call seems to be FREEZING code occasionally
            if self.debug and time.time() - last_time > 5:
                self.debug_print(f"Longer than normal runtime: {status}")
                last_time = time.time()
            await asyncio.sleep(1)

        self.debug_print("Status: " + status)

        # run no longer in progress, handle each possible run condition
        if status == "requires_action":  # delegate tool calls to __function_manager()
            calls = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id, run_id=self.run_id
            ).required_action  # also FREEZING after this call
            self.__function_manager(calls)
            return await self.__run_manager()
        elif status == "completed":  # return response
            self.run_id = None
            return (
                self.client.beta.threads.messages.list(self.thread_id)
                .data[0]
                .content[0]
                .text.value
            )
        elif status == "failed":  # something went wrong
            # BUG should probably handle this better
            # and retry run up to max attempts
            # though we have not seen a run fail yet
            self.run_id = None
            self.reg_print("Run failed")
            self.reg_print(
                self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread_id, run_id=run.id
                )
            )

    # Handle tool call responses
    def __function_manager(self, calls):
        self.debug_print("Managing functions")

        # empty array to hold multiple tool calls
        tool_outputs = []
        code = ""

        # iterate through all tool calls in run
        for toolCall in calls.submit_tool_outputs.tool_calls:
            # get attributes of tool call: id, function, arguments
            id = toolCall.id
            name = toolCall.function.name
            self.verbose_print(toolCall.function.arguments)
            try:
                args = json.loads(toolCall.function.arguments)
            except:
                self.debug_print("Error loading json, retyring")  # untested
                self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread_id,
                    run_id=self.run_id,
                    tool_outputs=tool_outputs,
                )
                return
            # handling for each available function call
            if name == "get_feedback":
                # print arg to command line and get written response from human
                self.reg_print(f"Hey Human, {args['prompt']}")
                human_response = input()
                tool_outputs.append({"tool_call_id": id, "output": human_response})
            elif name == "get_documentation":
                self.debug_print(f"Querying documentation for: {args['query'].lower()}")

                # search queryDict json file for requested term
                # BUG if chat has issues requesting exact term we could introduce
                # a semantic relation search upon 0 zero result
                for aClass in self.queryDict["class"]:
                    if aClass["name"] == args["query"].lower():
                        query_response = aClass
                        break
                    else:
                        query_response = (
                            "No available information on "
                            + args["query"].lower()
                            + ". Try rephrasing the term you are querying, \
                                for example changing underscores or phrasing, \
                                or alternatively ask the human for help."
                        )
                self.verbose_print(query_response)
                tool_outputs.append(
                    {"tool_call_id": id, "output": json.dumps(query_response)}
                )
            elif name == "run_code":
                code = args["code"]
                runtime = int(args["runtime"])  # in seconds
                code = code.replace("\n ", "\n")
                code = "\n" + code + "\n\n"
                code = code.replace("\n", "\r\n")
                self.debug_print(self.__print_break("RUNNING CODE", code))

                # send code to serial and get repl output
                # self.debug_print(self.__print_break("SERIAL OUTPUT", serial_response))
                self.debug_print("\n================== SERIAL OUPUT ==================")
                serial_response = self.serial_interface.serial_write(
                    bytes(code, "utf-8")
                )
                self.debug_print(serial_response)
                # send repl output back to assistant

                # kill code after runtime duration
                last_time = time.time()
                while time.time() < last_time + runtime:
                    temp_response = str(self.serial_interface.serial_read())
                    if temp_response != "":
                        self.debug_print(temp_response)
                        serial_response = serial_response + "\n" + temp_response
                    time.sleep(0.5)

                tool_outputs.append({"tool_call_id": id, "output": serial_response})
                self.debug_print("==================== END ====================")

                self.serial_interface.serial_write(bytes("\x03", "utf-8"))
                self.debug_print("Program ended")
            elif name == "get_visual_feedback":
                # BUG need to time running code with photos
                query = args["query"]  # desired information about images
                num_images = int(args["image_num"])  # number of images to be taken
                interval = int(args["interval"])  # time interval between images

                self.debug_print(f"Getting visual feedback for: {query.lower()}")

                img_response = (
                    self.__img_collection(query, num_images, interval)
                    .choices[0]
                    .message.content
                )

                # attach response to tool outputs
                self.debug_print(img_response)
                tool_outputs.append(
                    {"tool_call_id": id, "output": json.dumps(img_response)}
                )

        # submit all collected tool call responses
        self.verbose_print(f"Submitting tool outputs: {tool_outputs}")
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread_id, run_id=self.run_id, tool_outputs=tool_outputs
        )  # BUG also FREEZING here
        self.debug_print("Done submitting outputs")

    def __encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def __img_collection(self, query, num, interval):
        # collect images from webcam
        self.debug_print("TAKING IMAGES IN 3 SECONDS")
        time.sleep(3)
        self.debug_print("Say cheese!")
        images = []
        for i in range(num):
            ret, frame = self.cam.read()
            cv.imwrite("image" + str(i) + ".jpg", frame)
            base64_image = self.__encode_image("image" + str(i) + ".jpg")
            url = f"data:image/jpeg;base64,{base64_image}"
            images.append(url)
            time.sleep(interval)

        # format images and query together for api call
        content = []
        prefix = f"These are {num} images taking with {interval} seconds in between. "
        content.append({"type": "text", "text": prefix + query})
        for img in images:
            new_image = {
                "type": "image_url",
                "image_url": {
                    "url": img,
                },
            }
            content.append(new_image)

        # send images and query to vision api
        response = self.client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            max_tokens=300,
        )
        self.debug_print("Sent photos")
        return response

    # Formtting functions
    def extract_code(self, result):
        if result.find("```") == -1:
            return ("", result)
        idx1 = result.find("```") + 3 + 7
        idx2 = result[idx1:].find("```") + idx1
        code = result[idx1:idx2]
        response = (
            result[: idx1 - 10] + self.__print_break("CODE", code) + result[idx2 + 3 :]
        )
        return (code, response)

    # Format content for text output
    def __print_break(self, name, body):
        result = f"""\n================== {name} ==================
        {body}
==================== END ===================="""
        return result

    # Printing functions (also write to the log file)
    def reg_print(self, text):
        self.log_print(text)
        print(text)

    def debug_print(self, text):
        if text.find("===") == -1 and text.find(">>>") == -1:
            prefix = " - Status: "
        else:
            prefix = ""

        self.log_print(prefix + text)
        if self.debug:
            print(prefix + text)

    def verbose_print(self, text):
        self.log_print(text)
        if self.verbose:
            print(f"{text}")

    def log_print(self, text):
        self.this_log.write("\n" + str(text))
        self.all_log.write("\n" + str(text))

    # Public method to start the OpenAI run asynchronously
    async def run(self, message):
        self.add_message(message)
        result = await self.__run_manager()  # Await the result from __run_manager
        return result

    def close(self):
        self.debug_print("Closing")
        self.this_log.close()
        self.all_log.close()
        self.kill_all_runs()
        print("Files closed and runs killed")
