from openai import OpenAI
import cv2 as cv
import time
import asyncio
import json
import sys
import serial_interface
import base64

### private variables
# assistant_id
# thread_id
# client_id
# run_id
# queryDict

### ACTION ITEMS ###
# - ALWAYS: expand json file with more SPIKE syntax
# - ALWAYS: improve commenting and readability
#
# - TODO: !!! handle errors and hanging api calls
# - TODO: !!! Clean up text output and make more presentable
# - TODO: tailor assistant instructions to get better function calling behavior
# - TODO: create functionality for a debug log exported as txt file
#
# - BUG: json.decoder.JSONDecodeError: Invalid \escape: line 2 column 41 (char 42)
#        occurs in __functionManager() on line 174
# - BUG: freezing after "Run in Progress" and "Submitting tool outputs"
#        seems to be an issue on the openAI end
#        search file for "FREEZING" to find occurances
# - BUG: chatGPT indentaton does not mesh well with REPL
#        might be best to always parse the response and delete all spaces after new line if possible


class openAIAlchemy:
    def __init__(self, assistant_id, thread_id=None, debug=False):
        self.client = OpenAI()
        # self.killAllRuns()
        self.assistant_id = assistant_id
        self.debug = debug
        self.run_id = None
        self.queryDict = json.load(open("queryDict.json", "r"))
        self.cam = cv.VideoCapture(0)

        if thread_id == None:
            newThread = self.client.beta.threads.create()
            self.thread_id = newThread.id
            if self.debug:
                print("THREAD_ID: ", self.thread_id)
        else:
            self.thread_id = thread_id

    # Public Function
    # Change model of current assistant
    # Options: "gpt-4", "gpt-3.5"
    def changeModel(self, modelNum):
        models = ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo-0125"]
        self.client.beta.assistants.update(
            self.assistant_id,
            model=models[modelNum],
        )

    # Public Debugging Function
    # Retreive assistants for purpose of finding IDs
    def getAssistants(self):
        my_assistants = self.client.beta.assistants.list(
            order="desc",
            limit="20",
        )
        return my_assistants.data

    # Public Debugging Function
    # Retrieve all runs in a current thread
    def getRuns(self):
        runs = self.client.beta.threads.runs.list(self.thread_id)
        return runs

    # Public Debugging Function
    # Kills all runs that are in progress or requiring action
    def killAllRuns(self):
        runs = self.getRuns()
        for run in runs.data:
            if run.status == "in_progress" or run.status == "requires_action":
                self.client.beta.threads.runs.cancel(
                    thread_id=self.thread_id, run_id=run.id
                )

    # Public Debugging Function
    # Add message to current thread
    def addMessage(self, message):
        if self.debug:
            print("Adding Message")
        self.client.beta.threads.messages.create(
            self.thread_id,
            role="user",
            content=message,
        )

    # Public Debugging Function
    # Get most recent message from the thread
    def getMessage(self):
        messages = self.client.beta.threads.messages.list(self.thread_id)
        return messages.data[0].content[0].text.value

    # Private Function
    # Start and / or manage run of current thread
    async def __runManager(self):
        if self.run_id == None:  # check for existing run
            if self.debug:
                print("Creating new run")
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread_id, assistant_id=self.assistant_id
            )  # BUG FREEZING HERE
            self.run_id = run.id
        else:
            if self.debug:
                print("Using existing run")
        if self.debug:
            print("Run in progress")
        status = "in_progress"

        # entering status monitoring loop
        # exits upon completion, failure, or tool call response required
        lastTime = time.time()
        while status not in ["completed", "failed", "requires_action"]:
            status = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id, run_id=self.run_id
            ).status  # BUG this api call seems to be FREEZING code occasionally
            if self.debug and time.time() - lastTime > 5:
                print("Longer than normal runtime: ", status)
                lastTime = time.time()
            await asyncio.sleep(1)

        if self.debug:
            print("Status: " + status)

        # run no longer in progress, handle each possible run condition
        if status == "requires_action":  # delegate tool calls to __functionManager()
            calls = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id, run_id=self.run_id
            ).required_action  # also FREEZING after this call
            self.__functionManager(calls)
            return await self.__runManager()
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
            print("Run Failed")
            print(
                self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread_id, run_id=run.id
                )
            )

    # Format content for text output
    def __print_break(self, name, body):
        print("==================== " + name + " ====================")
        print(body)
        print("==================== " + "end" + " ====================")

    # Handle tool call responses
    def __functionManager(self, calls):
        if self.debug:
            print("Managing functions")

        # empty array to hold multiple tool calls
        tool_outputs = []

        # iterate through all tool calls in run
        for toolCall in calls.submit_tool_outputs.tool_calls:
            # get attributes of tool call: id, function, arguments
            id = toolCall.id
            name = toolCall.function.name
            print(toolCall.function.arguments)
            args = json.loads(
                toolCall.function.arguments
            )  # BUG source of some errors, put into try and catch

            # handling for each available function call
            if name == "get_feedback":
                # print arg to command line and get written response from human
                print("Hey Human, ", args["prompt"])
                human_response = input()
                tool_outputs.append({"tool_call_id": id, "output": human_response})
            elif name == "get_documentation":
                if self.debug:
                    print("Querying Documentation for: ", args["query"].lower())

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
                            + ". Try rephrasing the term you are querying, for example changing underscores or phrasing, or alternatively ask the human for help."
                        )
                if self.debug:
                    print(query_response)
                tool_outputs.append(
                    {"tool_call_id": id, "output": json.dumps(query_response)}
                )
            elif name == "run_code":
                code = args["code"]  # micro python formatted code
                runtime = int(args["runtime"])  # runtime in seconds until kill code
                code = code.replace("\n", "\r\n")
                self.__print_break("RUNNING CODE", code)

                # send code to serial and get repl output
                serial_response = serial_interface.serial_write(bytes(code, "utf-8"))
                if self.debug:
                    self.__print_break("SERIAL OUTPUT", serial_response)

                # send repl output back to assistant
                tool_outputs.append({"tool_call_id": id, "output": serial_response})

                # kill code after runtime duration
                time.sleep(runtime)
                print("ending program")
                serial_interface.serial_write(bytes("\x03", "utf-8"))
                print("Program successfully ended")
            elif name == "get_visual_feedback":
                # BUG need to time running code with photos
                query = args["query"]  # desired information about images
                num_images = int(args["image_num"])  # number of images to be taken
                interval = int(args["interval"])  # time interval between images

                if self.debug:
                    print("Getting visual feedback for: ", query.lower())

                img_response = (
                    self.__imgCollection(query, num_images, interval)
                    .choices[0]
                    .message.content
                )

                # attach response to tool outputs
                if self.debug:
                    print(img_response)
                tool_outputs.append(
                    {"tool_call_id": id, "output": json.dumps(img_response)}
                )

        # submit all collected tool call responses
        if self.debug:
            print("Submitting Tool Outputs: ", tool_outputs)
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread_id, run_id=self.run_id, tool_outputs=tool_outputs
        )  # BUG also FREEZING here
        print("done submitting outputs")

    def __encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def __imgCollection(self, query, num, interval):
        # collect images from webcam
        if self.debug:
            print("TAKING IMAGES IN 3 SECONDS")
            time.sleep(3)
            print("Say Cheese!")
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
        content.append({"type": "text", "text": query})
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
        if self.debug:
            print("Sent photos")
        return response

    def extract_code(self, result):
        idx1 = result.find("```") + 3 + 7
        idx2 = result[idx1:].find("```") + idx1
        code = result[idx1:idx2]
        breaker = "============ CODE ============\n"
        breaker1 = "==============================\n"
        response = result[: idx1 - 10] + breaker + code + breaker1 + result[idx2 + 3 :]

        return (code, response)

    def serialTalk(self, code):
        pass

    # Public method to start the OpenAI run asynchronously
    async def run(self, message):
        self.addMessage(message)
        result = await self.__runManager()  # Await the result from __runManager
        return result  # Return the
