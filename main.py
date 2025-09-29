import streamlit as st
import os
import json
import urllib.request
import urllib.error
import urllib.parse
import time
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
    
    # Show relevant settings based on selected bot
    if selected_bot == "Gemini Bot":
        st.subheader("Gemini Bot Settings")
        has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
        st.caption(f"API Key: {'✓' if has_gemini_key else '✗'}")
        if not has_gemini_key:
            st.info("Add GEMINI_API_KEY to .env file")
            
    elif selected_bot == "Image Bot":
        st.subheader("Image Bot Settings")
        comfy_base_url = st.text_input(
            "ComfyUI URL", 
            value=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        )
        
        if st.button("Test ComfyUI"):
            try:
                with urllib.request.urlopen(f"{comfy_base_url.rstrip('/')}/system_stats", timeout=5) as resp:
                    if resp.status == 200:
                        st.success("ComfyUI connected!")
                    else:
                        st.error(f"Error: {resp.status}")
            except Exception as e:
                st.error(f"Cannot connect: {str(e)[:100]}")
    
    else:  # Echo Bot
        st.subheader("Echo Bot Settings")
        st.caption("No setup required - just start chatting!")
    
    st.divider()
    
    # Clear chat
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
else:  # Image Bot
    st.title("Image Bot")
    st.caption("Describe an image and I'll generate it for you!")

# Helper functions
def get_echo_response(user_message):
    """Get response from Echo Bot - simply echoes the user's input"""
    return f"You said: **{user_message}**"

def get_image_bot_response(user_message):
    """Get response from Image Bot - focuses on image generation"""
    return f"I'll generate an image for you: **{user_message}**"

def get_gemini_response(user_message):
    """Get response from Gemini API"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ No Gemini API key found. Add GEMINI_API_KEY to .env file."
    
    try:
        # Build conversation history
        contents = []
        for msg in st.session_state["messages"][-10:]:  # Last 10 messages
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        # Add current message
        contents.append({"role": "user", "parts": [{"text": user_message}]})
        
        # API request
        payload = json.dumps({
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000,
            }
        }).encode("utf-8")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        req = urllib.request.Request(
            url=url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            
            if not candidates:
                return "⚠️ No response from Gemini."
            
            parts = (candidates[0].get("content") or {}).get("parts") or []
            if not parts or not parts[0].get("text"):
                return "⚠️ Empty response from Gemini."
            
            return parts[0]["text"].strip()
            
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return "⚠️ Invalid request to Gemini API."
        elif e.code == 403:
            return "⚠️ Gemini API access denied. Check your API key."
        else:
            return f"⚠️ Gemini API error ({e.code})"
    except Exception as e:
        return f"⚠️ Failed to call Gemini API: {str(e)[:200]}"

def should_generate_image(text):
    """Check if user wants an image generated"""
    keywords = [
        'generate', 'create', 'make', 'draw', 'paint', 'show me', 'image of', 
        'picture of', 'photo of', 'illustration of', 'artwork of', 'render',
        'visualize', 'design', 'sketch', 'art', 'painting', 'drawing'
    ]
    return any(keyword in text.lower() for keyword in keywords)

def load_workflow():
    """Load ComfyUI workflow"""
    try:
        here = os.path.dirname(__file__)
        wf_path = os.path.join(here, "comfy_workflow.json")
        if os.path.exists(wf_path):
            with open(wf_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading workflow: {e}")
    return None

def inject_prompt(workflow, prompt):
    """Inject prompt into workflow"""
    nodes = workflow.get("prompt", workflow)
    
    for node_id, node in list(nodes.items()):
        if isinstance(node, dict) and node.get("class_type") == "CLIPTextEncode":
            if "inputs" in node:
                node["inputs"]["text"] = prompt
                return workflow

def generate_comfy_image(prompt, base_url):
    """Generate image using ComfyUI"""
    workflow = load_workflow()
    if not workflow:
        return None, "No workflow file found"
    
    workflow = inject_prompt(workflow, prompt)
    payload_prompt = workflow.get("prompt", workflow)
    
    try:
        # Submit to ComfyUI
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
        
        # Wait for completion
        for _ in range(60):  # Wait up to 60 seconds
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
else:  # Image Bot
    user_input = st.chat_input("Describe an image you want me to generate...")

# Process user input
if user_input:
    # Add user message
    st.session_state["messages"].append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Generate response
    with st.chat_message("assistant"):
        # Get response based on selected bot
        if selected_bot == "Echo Bot":
            response = get_echo_response(user_input)
            st.markdown(response)
            assistant_msg = {"role": "assistant", "content": response}
            
        elif selected_bot == "Gemini Bot":
            response = get_gemini_response(user_input)
            st.markdown(response)
            assistant_msg = {"role": "assistant", "content": response}
            
        else:  # Image Bot
            response = get_image_bot_response(user_input)
            st.markdown(response)
            assistant_msg = {"role": "assistant", "content": response}
            
            # Always generate image for Image Bot
            st.write("Generating image...")
            image_url, error = generate_comfy_image(user_input, comfy_base_url)
            
            if image_url:
                st.image(image_url, caption=user_input)
                assistant_msg["image_url"] = image_url
            else:
                st.error(f"Image generation failed: {error}")
        
        # Add assistant message
        st.session_state["messages"].append(assistant_msg)

# Footer
st.divider()
if selected_bot == "Echo Bot":
    st.caption("💡 **Tip:** I'll echo back whatever you type!")
elif selected_bot == "Gemini Bot":
    st.caption("💡 **Tip:** Ask me questions, request help, or have a conversation!")
else:  # Image Bot
    st.caption("💡 **Tip:** Describe what you want to see - be creative and detailed!")