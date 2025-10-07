import streamlit as st
import os
import json
import urllib.request
import urllib.error
import urllib.parse
import time
import random
from dotenv import load_dotenv


st.set_page_config(
    page_title="AI Assistant",
    layout="wide"
)

# Load environment variables
load_dotenv()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Sidebar
with st.sidebar:
    st.header("Choose Your Assistant")
    
    # Bot selection
    selected_bot = st.selectbox(
        "What would you like to do?", 
        ["Echo Bot", "Gemini Bot", "Image Bot"], 
        help="Select the type of assistant you need"
    )
    
    st.divider()
    
    if selected_bot == "Gemini Bot":
        st.subheader("Gemini Bot Settings")
        has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
        st.caption(f"API Key: {'✓' if has_gemini_key else '✗'}")
        if not has_gemini_key:
            st.info("Add GEMINI_API_KEY to .env file")
            
    elif selected_bot == "Image Bot":
        st.subheader("🖼️ Image Bot Settings")
        comfy_base_url = st.text_input(
            "ComfyUI URL", 
            value=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        )

        # 🔧 Added: Generation parameters
        st.markdown("### Generation Parameters")
        width = st.number_input("Width", 256, 2048, 512, step=64)
        height = st.number_input("Height", 256, 2048, 512, step=64)
        batch_size = st.number_input("Batch Size", 1, 8, 1)
        steps = st.slider("Steps", 1, 50, 20)
        cfg = st.slider("CFG Scale", 1.0, 20.0, 8.0)
        randomize_seed = st.checkbox("Randomize Seed", True)
        seed = random.randint(0, 2**63 - 1) if randomize_seed else st.number_input("Seed", 0, 999999999, 12345)

        st.session_state["image_params"] = {
            "width": width,
            "height": height,
            "batch_size": batch_size,
            "steps": steps,
            "cfg": cfg,
            "seed": seed
        }

        if st.button("Test ComfyUI"):
            try:
                with urllib.request.urlopen(f"{comfy_base_url.rstrip('/')}/system_stats", timeout=5) as resp:
                    if resp.status == 200:
                        st.success("ComfyUI connected!")
                    else:
                        st.error(f"Error: {resp.status}")
            except Exception as e:
                st.error(f"Cannot connect: {str(e)[:100]}")
    
    else:
        st.subheader("Echo Bot Settings")
        st.caption("No setup required - just start chatting!")
    
    st.divider()
    
    if st.button("Clear Chat"):
        st.session_state["messages"] = []
        st.rerun()

# Main interface
if selected_bot == "Echo Bot":
    st.title("Echo Bot")
    st.caption("I'll echo back whatever you say!")
elif selected_bot == "Gemini Bot":
    st.title("Gemini Bot")
    st.caption("Ask me anything - I'm powered by Google's Gemini AI")
else:
    st.title("Image Bot")
    st.caption("Describe an image and I'll generate it for you!")

# Helper functions
def load_workflow():
    try:
        here = os.path.dirname(__file__)
        wf_path = os.path.join(here, "comfy_workflow.json")
        if os.path.exists(wf_path):
            with open(wf_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading workflow: {e}")
    return None

def inject_parameters(workflow, params):
    """🔧 Inject parameters like width, height, batch_size, seed, cfg, steps into workflow"""
    nodes = workflow.get("prompt", workflow)
    for node_id, node in list(nodes.items()):
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == "EmptyLatentImage":
            node["inputs"]["width"] = params["width"]
            node["inputs"]["height"] = params["height"]
            node["inputs"]["batch_size"] = params["batch_size"]
        elif node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = params["seed"]
            node["inputs"]["steps"] = params["steps"]
            node["inputs"]["cfg"] = params["cfg"]
    return workflow

def inject_prompt(workflow, prompt):
    nodes = workflow.get("prompt", workflow)
    for node_id, node in list(nodes.items()):
        if isinstance(node, dict) and node.get("class_type") == "CLIPTextEncode":
            if "inputs" in node:
                node["inputs"]["text"] = prompt
    return workflow

def generate_comfy_image(prompt, base_url, params):
    workflow = load_workflow()
    if not workflow:
        return None, "No workflow file found"

    workflow = inject_parameters(workflow, params)
    workflow = inject_prompt(workflow, prompt)
    payload_prompt = workflow.get("prompt", workflow)
    
    try:
        data = json.dumps({"prompt": payload_prompt}).encode("utf-8")
        req = urllib.request.Request(
            url=f"{base_url.rstrip('/')}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            enq = json.loads(resp.read().decode("utf-8"))
        
        prompt_id = enq.get("prompt_id")
        if not prompt_id:
            return None, "No prompt ID returned"
        
        # Wait for generation
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"{base_url.rstrip('/')}/history/{prompt_id}", timeout=10) as r:
                    hist = json.loads(r.read().decode("utf-8"))
            except Exception:
                time.sleep(1)
                continue
            
            if not hist:
                time.sleep(1)
                continue
            
            item = hist.get(prompt_id) or {}
            outputs = item.get("outputs") or {}
            
            for node_id, node_out in outputs.items():
                images = node_out.get("images") or []
                if images:
                    img = images[0]
                    filename = img.get("filename")
                    subfolder = img.get("subfolder", "")
                    img_type = img.get("type", "output")
                    
                    if filename:
                        image_url = f"{base_url.rstrip('/')}/view?filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type={urllib.parse.quote(img_type)}"
                        return image_url, ""
            
            time.sleep(1)
        
        return None, "Generation timed out"
        
    except Exception as e:
        return None, f"Error: {str(e)[:200]}"

# Chat display
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image_url" in message:
            st.image(message["image_url"], caption="Generated Image")

# Chat input
if selected_bot == "Echo Bot":
    user_input = st.chat_input("Type something and I'll echo it back...")
elif selected_bot == "Gemini Bot":
    user_input = st.chat_input("Ask me anything...")
else:
    user_input = st.chat_input("Describe an image you want me to generate...")

# Process user input
if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    with st.chat_message("assistant"):
        if selected_bot == "Echo Bot":
            response = f"You said: **{user_input}**"
            st.markdown(response)
            assistant_msg = {"role": "assistant", "content": response}
            
        elif selected_bot == "Gemini Bot":
            response = get_gemini_response(user_input)
            st.markdown(response)
            assistant_msg = {"role": "assistant", "content": response}
            
        else:
            response = f"I'll generate an image for you: **{user_input}**"
            st.markdown(response)
            assistant_msg = {"role": "assistant", "content": response}
            
            st.write("Generating image...")
            image_params = st.session_state.get("image_params", {})
            image_url, error = generate_comfy_image(user_input, comfy_base_url, image_params)
            
            if image_url:
                st.image(image_url, caption=user_input)
                assistant_msg["image_url"] = image_url
            else:
                st.error(f"Image generation failed: {error}")
        
        st.session_state["messages"].append(assistant_msg)

# Footer
st.divider()
if selected_bot == "Echo Bot":
    st.caption("💡 **Tip:** I'll echo back whatever you type!")
elif selected_bot == "Gemini Bot":
    st.caption("💡 **Tip:** Ask me questions, request help, or have a conversation!")
else:
    st.caption("💡 **Tip:** Describe what you want to see - be creative and detailed!")
