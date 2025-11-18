import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from pydub import AudioSegment
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, VideoProcessorBase
import av
import json
import io
import base64

st.set_page_config(page_title="Real-Time Interactive Multimedia Studio", layout="wide")

st.title("🎨 Real-Time Interactive Multimedia Studio (RIMS)")
st.write("A modern Flash-inspired Web Multimedia Studio built with Streamlit.")

if "frames" not in st.session_state:
    st.session_state.frames = []
if "current_color" not in st.session_state:
    st.session_state.current_color = "#000000"

tabs = st.tabs(["Drawing Studio", "Animation Timeline", "Camera & Mic", "Color Tools",
                "Video + Cue Points", "Export/Import"])

# -------------------------------------------------------------
# DRAWING STUDIO
# -------------------------------------------------------------
with tabs[0]:
    st.header("✏️ Drawing Studio")
    col1, col2 = st.columns([3, 1])

    with col2:
        color = st.color_picker("Color", value=st.session_state.current_color)
        st.session_state.current_color = color
        size = st.slider("Brush Size", 1, 50, 5)

    with col1:
        canvas_width = 600
        canvas_height = 400
        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8) + 255
        st.write("Draw on the canvas below (experimental):")
        img_file = st.camera_input("Use camera snapshot as background (optional)", key="bg")
        if img_file:
            bg_img = Image.open(img_file).resize((canvas_width, canvas_height))
            canvas = np.array(bg_img)

        draw_image = st.image(canvas, use_column_width=True)
        if st.button("Save Frame"):
            st.session_state.frames.append(canvas.tolist())
            st.success("Frame saved!")

# -------------------------------------------------------------
# ANIMATION TIMELINE
# -------------------------------------------------------------
with tabs[1]:
    st.header("🎞️ Animation Timeline")
    
    if st.session_state.frames:
        idx = st.slider("Select frame", 0, len(st.session_state.frames)-1, 0)
        st.image(np.array(st.session_state.frames[idx]), caption=f"Frame {idx}")
        
        if st.button("Play Animation"):
            for f in st.session_state.frames:
                st.image(np.array(f))
    else:
        st.info("No frames added yet.")

# -------------------------------------------------------------
# CAMERA & MIC
# -------------------------------------------------------------
with tabs[2]:
    st.header("📹 Camera & 🎤 Microphone")
    st.write("Live webcam stream:")

    class VideoProcessor(VideoProcessorBase):
        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            return av.VideoFrame.from_ndarray(img, format="bgr24")

    webrtc_streamer(key="camera", video_processor_factory=VideoProcessor)

# -------------------------------------------------------------
# COLOR TOOLS
# -------------------------------------------------------------
with tabs[3]:
    st.header("🎨 Color Theory Tools")
    color = st.color_picker("Pick a color")

    def rgb_to_gray(rgb):
        return int(0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2])

    rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    gray = rgb_to_gray(rgb)

    st.write("**Grayscale Equivalent:**", gray)

    st.write("**Web Safe Colors:**")
    websafe = [0, 51, 102, 153, 204, 255]
    palette = Image.new("RGB", (180, 180))
    draw = ImageDraw.Draw(palette)
    pos = 0
    for r in websafe:
        for g in websafe:
            for b in websafe:
                draw.rectangle([pos, 0, pos+5, 5], fill=(r,g,b))
                pos += 6
    st.image(palette)

# -------------------------------------------------------------
# VIDEO + CUE POINTS
# -------------------------------------------------------------
with tabs[4]:
    st.header("🎥 Video Playback with Cue Points")
    vid = st.file_uploader("Upload a video", type=["mp4", "mov"])
    cue_time = st.number_input("Add Cue Time (sec)", min_value=0)
    cue_action = st.text_input("Cue Action")

    if "cues" not in st.session_state:
        st.session_state.cues = []

    if st.button("Add Cue Point"):
        st.session_state.cues.append({"time": cue_time, "action": cue_action})
        st.success("Cue added!")

    st.write("Current Cue Points:", st.session_state.cues)

    if vid:
        st.video(vid)

# -------------------------------------------------------------
# EXPORT / IMPORT
# -------------------------------------------------------------
with tabs[5]:
    st.header("📦 Export / Import Project")

    project = {
        "frames": st.session_state.frames,
        "cues": st.session_state.get("cues", []),
    }

    json_data = json.dumps(project).encode()
    b64 = base64.b64encode(json_data).decode()
    href = f"<a href='data:file/json;base64,{b64}' download='project.json'>Download Project JSON</a>"
    st.markdown(href, unsafe_allow_html=True)

    uploaded = st.file_uploader("Import Project JSON", type=["json"])
    if uploaded:
        data = json.load(uploaded)
        st.session_state.frames = data["frames"]
        st.session_state.cues = data["cues"]
        st.success("Project loaded successfully!")
