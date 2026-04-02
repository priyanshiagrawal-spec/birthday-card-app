import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import io
import zipfile
import tempfile

def load_bold_font(size):
    """Load a bold font that's likely to be available on most systems"""
    try:
        # Try different bold system fonts in order of preference
        bold_font_options = [
            "Arial-Bold.ttf",
            "ArialBD.ttf",  # Windows Arial Bold
            "DejaVuSans-Bold.ttf",
            "Helvetica-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux path
            "/System/Library/Fonts/Helvetica-Bold.ttc",  # MacOS path
            "C:\\Windows\\Fonts\\arialbd.ttf"  # Windows path
        ]
        
        for font_path in bold_font_options:
            try:
                return ImageFont.truetype(font_path, size=size)
            except OSError:
                continue
        
        # If no bold fonts work, try regular fonts
        regular_font_options = [
            "Arial.ttf",
            "DejaVuSans.ttf",
            "Helvetica.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf"
        ]
        
        for font_path in regular_font_options:
            try:
                font = ImageFont.truetype(font_path, size=size)
                # Some PIL versions support font.font.style
                if hasattr(font, 'font') and hasattr(font.font, 'style'):
                    font.font.style = 'bold'
                return font
            except OSError:
                continue
                
        # If no system fonts work, use PIL's default font
        return ImageFont.load_default()
    except Exception as e:
        st.warning(f"Using basic font due to: {str(e)}")
        return ImageFont.load_default()

def get_centered_position(text, font, y_position, image_width):
    """Calculate the centered position for text"""
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    return ((image_width - text_width) // 2, y_position)

def preview_template(template, name, business, font, positions):
    """Generate a preview of the card with the updated name and business positions"""
    preview_img = template.copy()
    draw = ImageDraw.Draw(preview_img)

    name_position = get_centered_position(name, font, positions['name_y'], template.width)
    business_position = get_centered_position(f"({business})", font, positions['business_y'], template.width)

    if font == ImageFont.load_default():
        for offset in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            x, y = name_position
            draw.text((x + offset[0], y + offset[1]), name, fill="black", font=font)
            x, y = business_position
            draw.text((x + offset[0], y + offset[1]), f"({business})", fill="black", font=font)
    else:
        draw.text(name_position, name, fill="black", font=font)
        draw.text(business_position, f"({business})", fill="black", font=font)

    return preview_img

def generate_birthday_cards(df, templates, font_size, template_positions):
    """Generate birthday cards using multiple templates"""
    zip_buffer = io.BytesIO()
    
    with tempfile.TemporaryDirectory() as output_dir:
        font = load_bold_font(font_size)
        
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        num_templates = len(templates)
        
        for i, row in df.iterrows():
            status_text.text(f"Processing card {i+1} of {len(df)}: {row['Owner Name']}")
            
            # Select template based on index (cycling through templates)
            template_index = i % num_templates
            template = templates[template_index]
            positions = template_positions[template_index]
            
            name = row['Owner Name']
            business = row['Business Name']
            
            img = template.copy()
            draw = ImageDraw.Draw(img)
            
            name_position = get_centered_position(name, font, positions['name_y'], template.width)
            business_position = get_centered_position(f"({business})", font, positions['business_y'], template.width)
            
            if font == ImageFont.load_default():
                for offset in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                    x, y = name_position
                    draw.text((x + offset[0], y + offset[1]), name, fill="black", font=font)
                    x, y = business_position
                    draw.text((x + offset[0], y + offset[1]), f"({business})", fill="black", font=font)
            else:
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

# Initialize session state
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'template_positions' not in st.session_state:
    st.session_state.template_positions = []
if 'templates' not in st.session_state:
    st.session_state.templates = []

# Set page config
st.set_page_config(page_title="Multi-template Birthday Card Generator", layout="wide")

# Add custom CSS
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

# Excel file upload
st.markdown('<p class="upload-text">1. Upload Excel File</p>', unsafe_allow_html=True)
excel_file = st.file_uploader(
    "Must include 'Owner Name' and 'Business Name' columns",
    type=['xlsx']
)

# Multiple template upload
st.markdown('<p class="upload-text">2. Upload Template Images</p>', unsafe_allow_html=True)
template_files = st.file_uploader(
    "Select your birthday card templates (multiple files allowed)",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

# Font size adjustment - both slider and manual input
st.markdown("##### Font Size")
font_size_slider = st.slider("Adjust font size", min_value=10, max_value=150, value=25)
font_size_manual = st.number_input("Or enter font size manually", min_value=10, max_value=150, value=font_size_slider)
font_size = font_size_manual if font_size_manual else font_size_slider

# Template position adjustments - both slider and manual input
if template_files:
    st.session_state.templates = []
    st.session_state.template_positions = []
    
    for i, template_file in enumerate(template_files):
        st.markdown(f"##### Template {i+1} Positions")
        col1, col2 = st.columns(2)
        
        try:
            img = Image.open(template_file)
            st.session_state.templates.append(img)
            
            with col1:
                name_y_slider = st.slider(
                    f"Name position (Template {i+1})",
                    min_value=0,
                    max_value=img.height,
                    value=590 if img.height > 590 else img.height // 2,
                    key=f"name_{i}"
                )
                name_y_manual = st.number_input(f"Or enter Name position (Template {i+1})", min_value=0, max_value=img.height, value=name_y_slider)
            
            with col2:
                business_y_slider = st.slider(
                    f"Business position (Template {i+1})",
                    min_value=0,
                    max_value=img.height,
                    value=700 if img.height > 700 else img.height // 2,
                    key=f"business_{i}"
                )
                business_y_manual = st.number_input(f"Or enter Business position (Template {i+1})", min_value=0, max_value=img.height, value=business_y_slider)
            
            st.session_state.template_positions.append({
                'name_y': name_y_manual,
                'business_y': business_y_manual
            })
            
            # Preview
            font = load_bold_font(font_size)
            preview_image = preview_template(
                img,
                "Happy Birthday",
                "My Business",
                font,
                {'name_y': name_y_manual, 'business_y': business_y_manual}
            )
            st.image(preview_image, caption=f"Preview of Template {i+1}", width=400)
            
        except Exception as e:
            st.error(f"Error processing template {i+1}: {str(e)}")

# Generate button
if excel_file and template_files:
    if st.button("Generate Birthday Cards"):
        try:
            df = pd.read_excel(excel_file)
            
            required_columns = {'Owner Name', 'Business Name'}
            if not required_columns.issubset(df.columns):
                missing_cols = required_columns - set(df.columns)
                st.error(f"Missing required columns: {', '.join(missing_cols)}")
                st.stop()
            
            zip_buffer = generate_birthday_cards(
                df,
                st.session_state.templates,
                font_size,
                st.session_state.template_positions
            )
            st.session_state.zip_buffer = zip_buffer.getvalue()
            st.session_state.generated = True
            
            st.success("✅ All cards generated successfully!")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.stop()

# Download button
if st.session_state.generated and st.session_state.zip_buffer:
    st.download_button(
        label="📥 Download Birthday Cards",
        data=st.session_state.zip_buffer,
        file_name="Multiple_cards.zip",
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
