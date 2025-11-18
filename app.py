# app.py
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np
import io
import json
import zipfile
import time
import base64

st.set_page_config(page_title="RIMS Enhanced — Real-Time Interactive Multimedia Studio", layout="wide")
st.title("🎨 RIMS — Enhanced Real-Time Interactive Multimedia Studio")
st.write("Flash-inspired features: frames, tweening, camera, audio attach, cue points, export (no ML / no datasets).")

# --- Session state init ---
if "frames" not in st.session_state:
    st.session_state.frames = []  # list of PIL images
if "cues" not in st.session_state:
    st.session_state.cues = []
if "audio" not in st.session_state:
    st.session_state.audio = None
if "selected" not in st.session_state:
    st.session_state.selected = -1
if "playing" not in st.session_state:
    st.session_state.playing = False

# Helpers
def pil_from_np(img_np):
    return Image.fromarray(img_np.astype("uint8"))

def np_from_pil(img_pil):
    return np.array(img_pil)

def add_blank_frame(w=800, h=450, color=(255,255,255)):
    img = Image.new("RGB", (w,h), color=color)
    st.session_state.frames.append(img)
    st.session_state.selected = len(st.session_state.frames)-1

def get_frame_image(index):
    if 0 <= index < len(st.session_state.frames):
        return st.session_state.frames[index]
    return None

def remove_frame(index):
    if 0 <= index < len(st.session_state.frames):
        st.session_state.frames.pop(index)
        if st.session_state.frames:
            st.session_state.selected = max(0, index-1)
        else:
            st.session_state.selected = -1

def duplicate_frame(index):
    img = get_frame_image(index)
    if img:
        st.session_state.frames.insert(index+1, img.copy())
        st.session_state.selected = index+1

def reorder_frame(old, new):
    if old==new or old<0 or new<0 or old>=len(st.session_state.frames) or new>=len(st.session_state.frames):
        return
    frame = st.session_state.frames.pop(old)
    st.session_state.frames.insert(new, frame)
    st.session_state.selected = new

def blend_frames(img1, img2, alpha):
    return Image.blend(img1.convert("RGBA"), img2.convert("RGBA"), alpha).convert("RGB")

# --- Layout ---
left, right = st.columns([2,1])

with left:
    st.subheader("Canvas & Tools")
    canvas_w = st.number_input("Canvas width", min_value=320, max_value=1600, value=800, step=10)
    canvas_h = st.number_input("Canvas height", min_value=200, max_value=1000, value=450, step=10)
    mode = st.selectbox("Mode", ["Draw", "Erase", "Pan"])
    stroke_width = st.slider("Brush / Stroke width", 1, 80, 6)
    color = st.color_picker("Brush Color", "#000000")
    bg_choice = st.selectbox("Background", ["White", "Checker (transparent)", "Image from Webcam / Upload"])
    uploaded_bg = None
    if bg_choice == "Image from Webcam / Upload":
        uploaded_bg = st.file_uploader("Upload image (optional) as background", type=["png","jpg","jpeg"])
        cam_snap = st.camera_input("Or take webcam snapshot", key="cam_bg")
    else:
        cam_snap = None

    tools_col1, tools_col2, tools_col3 = st.columns(3)
    with tools_col1:
        if st.button("Add Blank Frame"):
            add_blank_frame(w=canvas_w, h=canvas_h)
    with tools_col2:
        if st.button("Duplicate Frame"):
            if st.session_state.selected>=0:
                duplicate_frame(st.session_state.selected)
            else:
                st.warning("No frame selected")
    with tools_col3:
        if st.button("Delete Frame"):
            if st.session_state.selected>=0:
                remove_frame(st.session_state.selected)
            else:
                st.warning("No frame selected")

    st.markdown("---")
    # Prepare initial image for canvas
    base_img = Image.new("RGB", (canvas_w, canvas_h), (255,255,255))
    if st.session_state.selected >= 0:
        frame_img = get_frame_image(st.session_state.selected)
        if frame_img:
            base_img = frame_img.resize((canvas_w, canvas_h))
    else:
        base_img = base_img

    # set background for canvas component
    if bg_choice == "Checker (transparent)":
        # create checkerboard as preview for transparency
        checker = Image.new("RGB", (canvas_w, canvas_h), (200,200,200))
        base_img = checker
    elif bg_choice == "Image from Webcam / Upload":
        if uploaded_bg:
            try:
                b = Image.open(uploaded_bg).convert("RGB").resize((canvas_w, canvas_h))
                base_img = b
            except:
                pass
        elif cam_snap:
            try:
                b = Image.open(cam_snap).convert("RGB").resize((canvas_w, canvas_h))
                base_img = b
            except:
                pass

    # Drawable canvas
    drawing_mode = "freedraw" if mode=="Draw" else ("transform" if mode=="Pan" else "freedraw")
    canvas_result = st_canvas(
        fill_color="rgba(0,0,0,0)",
        stroke_width=stroke_width,
        stroke_color=color,
        background_image=base_img,
        update_streamlit=True,
        height=canvas_h,
        width=canvas_w,
        drawing_mode=drawing_mode,
        key="canvas"
    )

    # Actions on canvas result
    if canvas_result.image_data is not None:
        img_np = canvas_result.image_data[:, :, :3]
        pil_img = pil_from_np(img_np)
        col_save, col_replace = st.columns(2)
        with col_save:
            if st.button("Save as New Frame"):
                st.session_state.frames.append(pil_img.copy())
                st.session_state.selected = len(st.session_state.frames)-1
                st.success("Saved as new frame.")
        with col_replace:
            if st.button("Replace Current Frame"):
                if st.session_state.selected >= 0:
                    st.session_state.frames[st.session_state.selected] = pil_img.copy()
                    st.success("Replaced current frame.")
                else:
                    st.warning("No frame selected to replace.")

    # Text tool
    st.markdown("**Text Tool (multilingual)**")
    text_input = st.text_area("Enter text to render on current frame (supports unicode):", "")
    font_size = st.slider("Font size", 12, 200, 36)
    text_x = st.number_input("X position", 0, canvas_w, 50)
    text_y = st.number_input("Y position", 0, canvas_h, 50)
    text_color = st.color_picker("Text color", "#000000", key="textcolor")
    if st.button("Render Text onto Frame"):
        if st.session_state.selected >= 0:
            img = get_frame_image(st.session_state.selected).copy()
            draw = ImageDraw.Draw(img)
            try:
                # Use default font (system). If available, PIL may render Unicode.
                font = ImageFont.truetype("DejaVuSans.ttf", font_size)
            except:
                font = ImageFont.load_default()
            draw.text((text_x, text_y), text_input, fill=text_color, font=font)
            st.session_state.frames[st.session_state.selected] = img
            st.success("Text rendered onto frame.")
        else:
            st.warning("No frame selected.")

with right:
    st.subheader("Frames & Timeline")
    cols = st.columns([1,1,1,1])
    with cols[0]:
        if st.button("⤴ Move Left"):
            if st.session_state.selected>0:
                reorder_frame(st.session_state.selected, st.session_state.selected-1)
    with cols[1]:
        if st.button("⤵ Move Right"):
            if st.session_state.selected < len(st.session_state.frames)-1:
                reorder_frame(st.session_state.selected, st.session_state.selected+1)
    with cols[2]:
        if st.button("Clear All"):
            st.session_state.frames = []
            st.session_state.selected = -1
            st.success("All frames cleared.")
    with cols[3]:
        if st.button("Add Blank (Default size)"):
            add_blank_frame()

    st.markdown("**Frame Thumbnails** (click to select)")
    thumb_cols = st.columns(4)
    for i, img in enumerate(st.session_state.frames):
        col = thumb_cols[i % 4]
        buf = io.BytesIO()
        img.resize((160,90)).save(buf, format="PNG")
        st_img = buf.getvalue()
        if col.button(f"Frame {i}", key=f"thumb_{i}"):
            st.session_state.selected = i
        col.image(st_img, use_column_width=True)

    st.markdown("---")
    st.write("**Selected Frame Preview**")
    if st.session_state.selected >= 0:
        sel_img = get_frame_image(st.session_state.selected)
        st.image(np_from_pil(sel_img), use_column_width=True)
    else:
        st.info("No frame selected.")

    st.markdown("---")
    st.write("**Tweening (Interpolation between two frames)**")
    c1 = st.number_input("Start frame index", min_value=0, max_value=max(0, len(st.session_state.frames)-1), value=0)
    c2 = st.number_input("End frame index", min_value=0, max_value=max(0, len(st.session_state.frames)-1), value=max(0, len(st.session_state.frames)-1))
    steps = st.slider("Number of in-between frames to generate (linear blend)", 0, 30, 5)
    if st.button("Generate Tween Frames (insert after end frame)"):
        if len(st.session_state.frames) >= 2 and c1 < len(st.session_state.frames) and c2 < len(st.session_state.frames) and c1!=c2:
            start = get_frame_image(c1).resize((canvas_w,canvas_h))
            end = get_frame_image(c2).resize((canvas_w,canvas_h))
            inserts = []
            for s in range(1, steps+1):
                alpha = s / (steps + 1)
                blended = blend_frames(start, end, alpha)
                inserts.append(blended)
            # insert after end frame index
            insert_index = max(c1,c2) + 1
            for idx, f in enumerate(inserts):
                st.session_state.frames.insert(insert_index+idx, f)
            st.success(f"Inserted {len(inserts)} tween frames.")
        else:
            st.warning("Need at least two distinct frames to tween.")

    st.markdown("---")
    st.write("**Playback controls**")
    speed = st.slider("Playback FPS", 1, 24, 6)
    play_col1, play_col2, play_col3 = st.columns(3)
    with play_col1:
        if st.button("Play Animation"):
            if st.session_state.frames:
                placeholder = st.empty()
                st.session_state.playing = True
                delay = 1.0 / float(max(1, speed))
                for f in st.session_state.frames:
                    if not st.session_state.playing:
                        break
                    placeholder.image(np_from_pil(f))
                    time.sleep(delay)
                st.session_state.playing = False
            else:
                st.warning("No frames to play.")
    with play_col2:
        if st.button("Stop"):
            st.session_state.playing = False
    with play_col3:
        if st.button("Export GIF Preview (temporary)"):
            if st.session_state.frames:
                buf = io.BytesIO()
                frames = [f.resize((640,360)) for f in st.session_state.frames]
                frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=int(1000/speed), loop=0)
                b = buf.getvalue()
                b64 = base64.b64encode(b).decode()
                href = f"<a href='data:image/gif;base64,{b64}' download='preview.gif'>Download GIF Preview</a>"
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning("No frames to export GIF.")

    st.markdown("---")
    st.write("**Video + Cue Points**")
    uploaded_video = st.file_uploader("Upload video (optional) for cue points", type=["mp4","mov","webm"])
    cue_time = st.number_input("Cue Time (sec)", min_value=0.0, value=0.0, step=0.5)
    cue_action = st.text_input("Cue Action / Label", "")
    if st.button("Add Cue Point"):
        st.session_state.cues.append({"time": float(cue_time), "action": cue_action})
        st.success("Cue added.")
    st.write(st.session_state.cues)
    if uploaded_video:
        st.video(uploaded_video)

    st.markdown("---")
    st.write("**Audio**")
    uploaded_audio = st.file_uploader("Upload audio file (optional, mp3/wav)", type=["mp3","wav","ogg"])
    if uploaded_audio:
        st.session_state.audio = uploaded_audio.getvalue()
        st.success("Audio uploaded and attached to project.")

st.markdown("---")
st.header("Project Export / Import")

# Prepare project JSON
project = {
    "frames_count": len(st.session_state.frames),
    "frames": [],  # we will not inline the binary images; we export as PNGs in ZIP
    "cues": st.session_state.cues,
}

# Export as ZIP (frames as PNG, project.json, audio if present)
if st.button("Export Project ZIP"):
    if not st.session_state.frames:
        st.warning("No frames to export.")
    else:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            # add frames
            for idx, img in enumerate(st.session_state.frames):
                b = io.BytesIO()
                img.save(b, format="PNG")
                zf.writestr(f"frames/frame_{idx:03d}.png", b.getvalue())
            # add project JSON (metadata)
            metadata = {
                "frames": [f"frames/frame_{i:03d}.png" for i in range(len(st.session_state.frames))],
                "cues": st.session_state.cues,
                "canvas_size": {"width": canvas_w, "height": canvas_h}
            }
            zf.writestr("project.json", json.dumps(metadata, indent=2))
            # add audio if present
            if st.session_state.audio:
                zf.writestr("audio/attached_audio", st.session_state.audio)
        zip_buf.seek(0)
        b64 = base64.b64encode(zip_buf.read()).decode()
        href = f"<a href='data:application/zip;base64,{b64}' download='rims_project.zip'>Download Project ZIP</a>"
        st.markdown(href, unsafe_allow_html=True)

# Import project JSON/ZIP
st.write("Import project: upload ZIP (exported by this app) or JSON (project.json)")
uploaded_project = st.file_uploader("Upload project ZIP/JSON", type=["zip","json"])
if uploaded_project is not None:
    content = uploaded_project.read()
    try:
        if uploaded_project.name.endswith(".zip"):
            z = zipfile.ZipFile(io.BytesIO(content))
            # read project.json
            pj = json.loads(z.read("project.json").decode())
            # load frames
            frames = []
            for fn in pj["frames"]:
                frames.append(Image.open(io.BytesIO(z.read(fn))).convert("RGB"))
            st.session_state.frames = frames
            st.session_state.cues = pj.get("cues", [])
            st.success("Project imported from ZIP.")
        else:
            pj = json.loads(content.decode())
            # user might have uploaded a project.json with references to frames not present -> warn
            if "frames" in pj and pj["frames"]:
                st.warning("JSON references frames by filename. Uploading standalone JSON will not include binary frames. Use the ZIP export instead for full project import.")
            st.session_state.cues = pj.get("cues", [])
            st.success("Project JSON imported (no frames).")
    except Exception as e:
        st.error(f"Failed to import project: {e}")

st.markdown("---")
