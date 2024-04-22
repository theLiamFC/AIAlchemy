from openai import OpenAI
import cv2 as cv
import time
import asyncio
import json
import base64
import re
from PIL import Image
from io import BytesIO


class AIAlchemy:
    def __init__(
        self, assistant_id, serial, thread_id=None, debug=False, verbose=False
    ):
        # Class assets
        self.query_dict = json.load(open("query_dict.json", "r"))
        self.cam = cv.VideoCapture(0)

        # Serial initiation
        self.serial_interface = serial
        self.serial_interface.open_new()
        self.serial_interface.write_read("\x03")

        # Logging
        self.verbose = verbose
        if self.verbose:
            self.debug = True
        else:
            self.debug = debug
        self.curr_code = ""
        log_path = "logs/"
        self.this_log = open(log_path + "this_log.txt", "w+")  # write (and read) over this file
        self.good_log = open(log_path + "good_log.txt", "a")  # append to this files
        self.all_log  = open(log_path + "all_log.txt", "a")  # append to this files
        
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.log_print(f"\n\n\nPROGRAM OUTPUT FROM {formatted_time}\n")

        # Core variables
        self.client = OpenAI()
        self.assistant_id = assistant_id
        self.run_id = None
        if thread_id == None:
            new_thread = self.client.beta.threads.create()
            self.thread_id = new_thread.id
            self.debug_print(f"THREAD_ID: {self.thread_id}")
        else:
            self.thread_id = thread_id


    ################################################################
    ####################   PUBLIC FUNCTIONS   ######################
    ################################################################

    # Change model of current assistant
    def change_model(self, modelNum):
        models = ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo-0125"]
        self.client.beta.assistants.update(
            self.assistant_id,
            model=models[modelNum],
        )

    # Retreive assistants for purpose of finding IDs
    def get_assistants(self):
        my_assistants = self.client.beta.assistants.list(
            order="desc",
            limit="20",
        )
        return my_assistants.data

    # Retrieve all runs in a current thread
    def get_runs(self):
        runs = self.client.beta.threads.runs.list(self.thread_id)
        return runs

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


    ################################################################
    ###################   PRIVATE FUNCTIONS   ######################
    ################################################################

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
        self.this_log.flush()

        # empty array to hold multiple tool calls
        tool_outputs = []
        code = ""

        # iterate through all tool calls in run
        for toolCall in calls.submit_tool_outputs.tool_calls:
            # get attributes of tool call: id, function, arguments
            id = toolCall.id
            name = toolCall.function.name
            self.verbose_print(toolCall.function.arguments)
            args = self.__clean_json(toolCall.function.arguments)
            
            # handling for each available function call
            if name == "get_feedback":
                # print arg to command line and get written response from human
                self.reg_print(f"ChatGPT: Hey Human, {args['prompt']}")
                human_response = input("Human: ")
                print()
                tool_outputs.append({"tool_call_id": id, "output": human_response})
            elif name == "get_documentation":
                self.reg_print(
                    f"ChatGPT: I am querying documentation for {args['query'].lower()}"
                )

                # search query_dict json file for requested term
                # BUG if chat has issues requesting exact term we could introduce
                # a semantic relation search upon 0 zero result
                for aClass in self.query_dict["class"]:
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
                original_code = args["code"]
                runtime = int(args["runtime"])  # in seconds

                serial_response = self.__run_code(original_code, runtime)
                tool_outputs.append({"tool_call_id": id, "output": serial_response})

            # Currently uninstalled
            elif name == "get_visual_feedback":
                # BUG need to time running code with photos
                query = args["query"]  # desired information about images
                num_images = int(args["image_num"])  # number of images to be taken
                interval = float(args["interval"])  # time interval between images

                self.debug_print(
                    f"ChatGPT: I am getting visual feedback for {query.lower()}"
                )

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


    ################################################################
    #####################   IMAGE CAPTURE   ########################
    ################################################################

    def __encode_image(self, image_path, max_image=512):
        with Image.open(image_path) as img:
            width, height = img.size
            max_dim = max(width, height)
            if max_dim > max_image:
                scale_factor = max_image / max_dim
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img = img.resize((new_width, new_height))

            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return img_str

    def __img_collection(self, query, num, interval):
        # collect images from webcam
        self.debug_print("Taking images IN 3 seconds")
        time.sleep(3)
        
        # NOTE to Liam: I (Jesse) added the code running and related serial sending
            # to a separate function, the only difference this makes here is that 
            # it does the same printing as above which maybe isn't wanted?
        repl = self.__run_code(self.curr_code, num * interval)
        # self.verbose_print(f"REPL response: {repl}")

        self.debug_print("Say cheese!")
        images = []
        for i in range(num):
            _, frame = self.cam.read()
            cv.imwrite("images/image" + str(i) + ".jpg", frame)
            base64_image = self.__encode_image("images/image" + str(i) + ".jpg")
            url = f"data:image/jpeg;base64,{base64_image}"
            images.append(url)
            time.sleep(interval)

        # format images and query together for api call
        content = []
        prefix = f"Here are {num} images taken with {interval} seconds in between.\
                    You can deduce motion by comparing differences between images. "
        new_query = prefix + query
        content.append({"type": "text", "text": new_query})
        for img in images:
            new_image = {
                "type": "image_url",
                "image_url": {
                    "url": img,
                },
            }
            content.append(new_image)

        # send images and query to vision api
        self.debug_print("Processing images")
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
        self.debug_print("Done")
        return response


    ################################################################
    #####################   CODE RUNNING   #########################
    ################################################################

    def __run_code(self, original_code, runtime):
        original_code = original_code.replace("\n ", "\n")
        code = "\n" + original_code

        code = code.replace("\n", "\r\n")
        self.curr_code = code
        self.reg_print(self.__print_break(f"RUNNING CODE ({runtime} second(s))"))
        self.reg_print(original_code)
        # ctrl D (reset the robot), ctrl C (reset terminal), ctr E (enter paste mode)
        self.log_print("RESETTING")
        self.debug_print(self.serial_interface.write_read("\x03"))
        self.debug_print(
            "Paste mode start: " + str(self.serial_interface.write_read("\x05"))
        )
        self.reg_print(self.__print_break("SERIAL OUPUT"))
        serial_response = self.serial_interface.write_read(code)
        self.debug_print(
            "Paste mode end: " + str(self.serial_interface.write_read("\x04"))
        )

        # Scan Response for ERROR and print if found
        # if re.search("error", serial_response.lower()):
        self.reg_print(serial_response)
        self.debug_print(serial_response)

        # Read in Serial For Duration of Runtime
        last_time = time.time()
        while time.time() < last_time + runtime:
            temp_response = str(self.serial_interface.read())
            lines = temp_response.split("\n")
            for line in lines:
                line = line.strip()
                if (
                    line != ""
                    and ">>>" not in line
                    and "<awaitable>" not in line
                ):
                    self.reg_print(line)
                    serial_response += "\n" + line
            time.sleep(0.5)

        self.reg_print(self.__print_break("END"))
        serial_response = self.serial_interface.write_read("\x04")

        # sends ctrl c to force end the program
        self.log_print(self.serial_interface.write_read("\x04"))
        self.serial_interface.close()
        self.serial_interface.open_new()
        self.serial_interface.write_read("\x03")

        self.debug_print("Program ended")
        return serial_response


    ################################################################
    ####################   LOGGING FUNCTIONS   #####################
    ################################################################

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
    def __print_break(self, name):
        length = len(name)
        breaker = ""
        for _ in range(40 - (int(length / 2))):
            breaker += "="
        if length % 2 == 0:
            suffix = "="
        else:
            suffix = ""
        result = breaker + " " + name + " " + breaker + suffix
        return result
    
    # If the AI assistant returns incorrectly formatted JSON clean before returning
    def __clean_json(self, json_text):
        try:
            return json.loads(json_text, strict=False)
        except:
            temp = json_text.split("\n")
            result = ""
            for line in temp:
                if line != "\\":
                    result += line + "\n"
            return json.loads(result, strict=False)

    # Printing functions (also write to the log file)
    def reg_print(self, text):
        self.log_print(text)
        print(text)
        print()

    def debug_print(self, text):
        if text.find("===") == -1 and text.find(">>>") == -1:
            prefix = " - Status: "
        else:
            prefix = ""
        self.log_print(prefix + str(text))
        if self.debug:
            print(prefix + str(text))

    def verbose_print(self, text):
        self.log_print(text)
        if self.verbose:
            print(text)

    def log_print(self, text):
        if "<awaitable>" not in text:
            self.this_log.write("\n" + str(text))
            self.all_log.write("\n" + str(text))

    # Public method to start the OpenAI run asynchronously
    async def run(self, message):
        self.add_message(message)
        result = await self.__run_manager()
        return result

    # Safely end program and save and close log files
    def close(self):
        self.debug_print("Closing")
        self.this_log.flush()
        self.this_log.seek(0)

        save = input("Would you like to save this run to the good_log.txt? (y/n)\n")
        if save.lower() == "y":
            message = input("Write saved message: ")
            self.good_log.write(f"\n\n\nThe run was good because: {message}\n\n")
            self.good_log.write(self.this_log.read())
            print("Saved to good_log.txt")
        self.this_log.close()
        self.good_log.close()
        self.all_log.close()

        self.kill_all_runs()
        print("Files closed and runs killed")
