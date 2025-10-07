A Streamlit-powered AI assistant for image generation using [ComfyUI](https://github.com/comfyanonymous/ComfyUI) as the backend. This bot provides a user-friendly web interface to generate images from text prompts, with full control over generation parameters.

---

## Tech Stack

- **Python**  
- **Streamlit** — Interactive UI and chat interface  
- **ComfyUI** — Image generation backend  
- **RESTful HTTP API** — Communication with ComfyUI  

---

## Features

- **Image Bot**
  - Generate images from text prompts using ComfyUI.
  - Customize image parameters: width, height, batch size, steps, CFG scale, seed.
  - Test connection to ComfyUI server from the sidebar.
  - View generated images directly in the chat interface.

- **Echo Bot**
  - Simple bot that echoes back user input.

- **Conversational UI**
  - Images and messages are displayed in a conversational format.

---

## Setup Instructions

### 1. Clone the Repository

```sh
git clone https://github.com/yourusername/gen-ai-personal-.git
cd gen-ai-personal-
```

### 2. Install Python Dependencies

Make sure you have Python 3.8+ installed.

```sh
pip install streamlit python-dotenv
```

### 3. Install and Run ComfyUI

- Follow the [ComfyUI installation guide](https://github.com/comfyanonymous/ComfyUI#installation) to set up the backend.
- For a video walkthrough, see [this tutorial](https://youtu.be/g74Cq9Ip2ik?si=BaPukdseq7u2UCra).
- Start the ComfyUI server (default URL: `http://127.0.0.1:8188`).

### 4. Prepare Workflow File

- Load your workflow `.json` file in the ComfyUI window.
- This file defines the image generation workflow for ComfyUI.
- You can modify the workflow in ComfyUI as needed.

### 5. Run the Streamlit App

If `streamlit` is not in your PATH, use:

```sh
python -m streamlit run main.py
```

Otherwise:

```sh
streamlit run main.py
```

---

## Usage

1. Open the app in your browser (Streamlit will provide a local URL).
2. Select "Image Bot" from the sidebar.
3. Configure image parameters as desired.
4. Enter a text prompt describing the image you want.
5. View the generated image in the chat interface.

---

## Troubleshooting

- **ComfyUI Connection Issues:**  
  - Ensure ComfyUI is running and accessible at the configured URL.
  - Use the "Test ComfyUI" button in the sidebar to verify connectivity.

- **Streamlit Not Found:**  
  - Use `python -m streamlit run main.py` if `streamlit` is not in your PATH.

- **Image Generation Fails:**  
  - Check that your workflow `.json` file exists and is valid.
  - Review error messages in the Streamlit interface for details.

---

## Refer

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [Streamlit](https://streamlit.io/)

---


