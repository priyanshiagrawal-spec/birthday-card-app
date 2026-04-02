import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import io
import zipfile
import tempfile

# ✅ FIXED FONT LOADER (works on cloud)
def load_bold_font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception as e:
        st.warning(f"Font not found, using default: {e}")
        return ImageFont.load_default()

def get_centered_position(text, font, y_position, image_width):
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    return ((image_width - text_width) // 2, y_position)

def preview_template(template, name, business, font, positions):
    preview_img = template.copy()
    draw = ImageDraw.Draw(preview_img)

    name_position = get_centered_position(name, font, positions['name_y'], template.width)
    business_position = get_centered_position(f"({business})", font, positions['business_y'], template.width)

    draw.text(name_position, name, fill="black", font=font)
    draw.text(business_position, f"({business})", fill="black", font=font)

    return preview_img

def generate_birthday_cards(df, templates, font_size, template_positions):
    zip_buffer = io.BytesIO()
    
    with tempfile.TemporaryDirectory() as output_dir:
        font = load_bold_font(font_size)
        
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        num_templates = len(templates)
        
        for i, row in df.iterrows():
            status_text.text(f"Processing card {i+1} of {len(df)}: {row['Owner Name']}")
            
            template_index = i % num_templates
            template = templates[template_index]
            positions = template_positions[template_index]
            
            name = row['Owner Name']
            business = row['Business Name']
            
            img = template.copy()
            draw = ImageDraw.Draw(img)
            
            name_position = get_centered_position(name, font, positions['name_y'], template.width)
            business_position = get_centered_position(f"({business})", font, positions['business_y'], template.width)
            
            draw.text(name_position, name, fill="black", font=font)
            draw.text(business_position, f"({business})", fill="black", font=font)
            
            output_file = os.path.join(output_dir, f"{business.replace(' ', '_')}.png")
            img.save(output_file)
            
            progress_bar.progress((i + 1) / len(df))
        
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_file.write(file_path, os.path.basename(file_path))
    
    status_text.empty()
    progress_bar.empty()
    return zip_buffer

# Session state
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'template_positions' not in st.session_state:
    st.session_state.template_positions = []
if 'templates' not in st.session_state:
    st.session_state.templates = []

st.set_page_config(page_title="Multi-template Birthday Card Generator", layout="wide")

st.markdown("""
<style>
.stButton>button {
    width: 100%;
}
.upload-text {
    font-size: 18px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("🎂 Multi-template Card Generator")

# Excel upload
st.markdown('<p class="upload-text">1. Upload Excel File</p>', unsafe_allow_html=True)
excel_file = st.file_uploader(
    "Must include 'Owner Name' and 'Business Name' columns",
    type=['xlsx']
)

# Template upload
st.markdown('<p class="upload-text">2. Upload Template Images</p>', unsafe_allow_html=True)
template_files = st.file_uploader(
    "Select templates",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

# Font size
st.markdown("##### Font Size")
font_size = st.slider("Adjust font size", 10, 150, 40)

# Template controls
if template_files:
    st.session_state.templates = []
    st.session_state.template_positions = []
    
    for i, template_file in enumerate(template_files):
        st.markdown(f"##### Template {i+1}")
        col1, col2 = st.columns(2)
        
        img = Image.open(template_file)
        st.session_state.templates.append(img)
        
        with col1:
            name_y = st.slider(f"Name Y {i+1}", 0, img.height, img.height // 2, key=f"name_{i}")
        with col2:
            business_y = st.slider(f"Business Y {i+1}", 0, img.height, img.height // 2 + 100, key=f"biz_{i}")
        
        st.session_state.template_positions.append({
            'name_y': name_y,
            'business_y': business_y
        })
        
        font = load_bold_font(font_size)
        preview = preview_template(
            img,
            "Happy Birthday",
            "My Business",
            font,
            {'name_y': name_y, 'business_y': business_y}
        )
        
        st.image(preview, width=400)

# Generate
if excel_file and template_files:
    if st.button("Generate Birthday Cards"):
        df = pd.read_excel(excel_file)
        
        required_columns = {'Owner Name', 'Business Name'}
        if not required_columns.issubset(df.columns):
            st.error("Missing required columns")
            st.stop()
        
        zip_buffer = generate_birthday_cards(
            df,
            st.session_state.templates,
            font_size,
            st.session_state.template_positions
        )
        
        st.session_state.zip_buffer = zip_buffer.getvalue()
        st.session_state.generated = True
        
        st.success("✅ Cards generated!")

# Download
if st.session_state.generated:
    st.download_button(
        "📥 Download Cards",
        data=st.session_state.zip_buffer,
        file_name="cards.zip",
        mime="application/zip"
    )
# Instructions
st.markdown("""
---
### 📝 Instructions

1. **Upload Excel File**
   - Must contain columns 'Owner Name' and 'Business Name'
   - File should be in .xlsx format

2. **Upload Template Images**
   - Upload multiple templates (PNG, JPG, JPEG)
   - Templates will be used in sequence (cycling through them)
   - For example, with 3 templates:
     * First person gets template 1
     * Second person gets template 2
     * Third person gets template 3
     * Fourth person gets template 1 again, and so on

3. **Adjust Settings for Each Template**
   - Set font size (applies to all templates)
   - Adjust name and business positions for each template individually
   - Preview shows how text will appear on each template

4. **Generate and Download**
   - Click "Generate Birthday Cards" to create all cards
   - Download the ZIP file containing all generated cards
""")
