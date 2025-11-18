import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, AudioProcessorBase
import av
import json
import base64

st.set_page_config(page_title="RIMS Multimedia Studio", layout="wide")
st.title("🎨 Real-Time Interactive Multimedia Studio (RIMS)")

# -------------------------------------------------------
# Initialize session state
# -------------------------------------------------------
if "frames" not in st.session_state:
    st.session_state.frames = []
if "current_color" not in st.session_state:
    st.session_state.current_color = "#000000"
if "cues" not in st.session_state:
    st.session_state.cues = []

tabs = st.tabs([
    "Drawing Studio", "Animation Timeline", "Camera Stream",
    "Audio Recording", "Color Tools", "Video + Cue Points",
    "Export / Import"
])

# -------------------------------------------------------
# Drawing Studio
# -------------------------------------------------------
with tabs[0]:
    st.header("✏️ Drawing Studio")

    col1, col2 = st.columns([3, 1])
    with col2:
        color = st.color_picker("Color", value=st.session_state.current_color)
        st.session_state.current_color = color
        brush_size = st.slider("Brush Size", 1, 50, 5)

    with col1:
        canvas_width, canvas_height = 600, 400
        canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255
        st.write("Canvas (static demo):")
        st.image(canvas)

        if st.button("Save Blank Frame"):
            st.session_state.frames.append(canvas.tolist())
            st.success("Frame saved!")

# -------------------------------------------------------
# Animation Timeline
# -------------------------------------------------------
with tabs[1]:
    st.header("🎞️ Animation Timeline")
    
    if st.session_state.frames:
        idx = st.slider(
            "Select frame", 0, len(st.session_state.frames) - 1, 0
        )
        st.image(np.array(st.session_state.frames[idx]))

        if st.button("Play Animation"):
            for f in st.session_state.frames:
                st.image(np.array(f))
    else:
        st.info("No frames saved yet. Add frames in Drawing Studio.")

# -------------------------------------------------------
# Camera Stream
# -------------------------------------------------------
with tabs[2]:
    st.header("📹 Camera Stream")

    class VideoProcessor(VideoProcessorBase):
        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            return av.VideoFrame.from_ndarray(img, format="bgr24")

    webrtc_streamer(key="camera", video_processor_factory=VideoProcessor)

# -------------------------------------------------------
# Audio Recording
# -------------------------------------------------------
with tabs[3]:
    st.header("🎤 Audio Recorder (Browser-based)")

    class AudioProcessor(AudioProcessorBase):
        def __init__(self):
            self.frames = []

        def recv_audio(self, frame):
            self.frames.append(frame)
            return frame

    ctx = webrtc_streamer(
        key="audio",
        mode="sendonly",
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False}
    )

    if ctx and ctx.audio_processor:
        if st.button("Save Recorded Audio"):
            if ctx.audio_processor.frames:
                frames = ctx.audio_processor.frames
                wav_bytes = b"".join([f.to_ndarray().tobytes() for f in frames])
                b64 = base64.b64encode(wav_bytes).decode()
                href = f"<a href='data:audio/wav;base64,{b64}' download='audio.wav'>Download audio.wav</a>"
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning("No audio recorded yet!")

# -------------------------------------------------------
# Color Tools
# -------------------------------------------------------
with tabs[4]:
    st.header("🎨 Color Tools")

    color = st.color_picker("Pick Color")
    r, g, b = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    gray = int(0.299*r + 0.587*g + 0.114*b)
    st.write("Grayscale value:", gray)

    st.write("Web Safe Colors:")
    ws = [0, 51, 102, 153, 204, 255]
    palette = Image.new("RGB", (180, 180))
    draw = ImageDraw.Draw(palette)
    pos = 0
    for R in ws:
        for G in ws:
            for B in ws:
                draw.rectangle([pos, 0, pos+5, 5], fill=(R,G,B))
                pos += 6
    st.image(palette)

# -------------------------------------------------------
# Video + Cue Points
# -------------------------------------------------------
with tabs[5]:
    st.header("🎥 Video + Cue Points")

    vid = st.file_uploader("Upload video", type=["mp4", "mov", "avi"])
    time = st.number_input("Cue time (sec)", min_value=0)
    action = st.text_input("Cue action")

    if st.button("Add Cue"):
        if action.strip():
            st.session_state.cues.append({"time": time, "action": action})
            st.success("Cue added!")
        else:
            st.warning("Enter a cue action!")

    if st.session_state.cues:
        st.write("Current Cue Points:")
        st.json(st.session_state.cues)
    else:
        st.info("No cue points added yet.")

    if vid:
        st.video(vid)

# -------------------------------------------------------
# Export / Import Project
# -------------------------------------------------------
with tabs[6]:
    st.header("📦 Export / Import Project")

    project = {
        "frames": st.session_state.frames,
        "cues": st.session_state.cues
    }

    data = json.dumps(project).encode()
    b64 = base64.b64encode(data).decode()
    href = f"<a href='data:file/json;base64,{b64}' download='project.json'>Download project.json</a>"
    st.markdown(href, unsafe_allow_html=True)

    uploaded = st.file_uploader("Import project", type=["json"])
    if uploaded:
        try:
            obj = json.load(uploaded)
            st.session_state.frames = obj.get("frames", [])
            st.session_state.cues = obj.get("cues", [])
            st.success("Project imported successfully!")
        except:
            st.error("Invalid JSON file!")
