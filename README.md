# OpenAI ChatGPT Robot Coding Interface

**See our project write-up and demo videos [here](https://jessewgilbert.com/ai-alchemy-demo)**

This repository is a work in progress authored by Jesse Gilbert and Liam Campbell for the Center for Engineering & Education Outreach ([CEEO](https://ceeo.tufts.edu/)) at Tufts University.

### Introduction

This project aims to facilitate collaboration between humans and artificial intelligence in coding robotics applications, specifically targeting the LEGO SPIKE Prime platform. By leveraging OpenAI's Assistant framework (which uses GPT-4), users can iteratively build programs alongside the AI, fostering learning opportunities for the user and accelerating robotic software projects. The program importantly flips the role of the user and AI, and enables AI to utilize the user as a resource for iterative coding development. In addition to asking the user for feedback, advice, and prompts, the AI is also enabled to query documentation, run code, and get visual feedback from a secondary OpenAI vision model.

### Usage

To use this repository, follow these steps:

- Ensure you have Python installed on your system.
- Clone this repository to your local machine.
- Install all required dependencies:
    - `pip install openai` (for calling the OpenAI API)
    - `pip install opencv-python` (for capturing images for the get_visual_feedback function)
    - `pip install pillow` (for opening images for the get_visual_feedback function)
    - `pip install serial` (for communicating with the robot of USB)
- Create an OpenAI API key [here](https://platform.openai.com/api-keys).
- Set up your API key by following the instructions [here](https://platform.openai.com/docs/quickstart/step-2-set-up-your-api-key).
- Plug in your LEGO SPIKE Prime to your computer and turn it on.
- Find the serial port of your LEGO SPIKE Prime device and update it in `main.py`.
- Run `main.py` to start the interactive AI powered coding session.

### File Descriptions

`ai_alchemy.py`: Contains the main class openAIAlchemy, which interfaces with the OpenAI API for communication.

`main.py`: Orchestrates the interaction between the user, ChatGPT, and the robot coding interface.

`serial_interface.py`: Handles all serial communication between the computer and LEGO SPIKE Prime.

`query_dict.json`: Contains necessary syntax and documentation for MicroPython coding on the LEGO SPIKE Prime platform. Ultimately we hope that this JSON file will be replaced by documentation built into the microcontroller itself. For now, we are using this isolated JSON documentation file to mimic the idea that the AI model has no pre-established knowledge of the robotic platform it is programming.
