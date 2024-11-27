from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, jsonify, session
import os
from werkzeug.utils import secure_filename
import requests
import json
import base64
from PIL import Image, ImageDraw, ImageFont, ImageColor
import textwrap
from PIL import ImageEnhance
import sys

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# OpenRouter configuration
OPENROUTER_API_KEY = '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'
SITE_URL = 'http://localhost:5000'
APP_NAME = 'LinkedIn Lunatic Meme Generator'

# Ensure upload folder exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'static', 'pictures')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

LINKEDIN_BLUE = "#0077B5"
STANDARD_WIDTH = 800  # Standard width for all images

# Font paths to try
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "C:\\Windows\\Fonts\\arial.ttf",  # Windows
    "Arial Bold.ttf",  # Current directory
    "arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

def get_font(size):
    """Try multiple font paths and return the first successful font"""
    for font_path in FONT_PATHS:
        try:
            font = ImageFont.truetype(font_path, size)
            print(f"Successfully loaded font from: {font_path} with size {size}")
            return font
        except Exception as e:
            print(f"Failed to load font from {font_path}: {str(e)}")
            continue
    
    print("WARNING: Using default font as no custom fonts could be loaded")
    return ImageFont.load_default()


def allowed_file(filename):
    return '.' in filename and filename.rsplit(
        '.', 1)[1].lower() in ALLOWED_EXTENSIONS


def resize_image(img, target_width):
    """Resize image to target width while maintaining aspect ratio"""
    aspect_ratio = img.size[1] / img.size[0]  # height / width
    target_height = int(target_width * aspect_ratio)
    return img.resize((target_width, target_height), Image.Resampling.LANCZOS)


def create_text_overlay(img_size, draw, text, font_size, font_path=None):
    print(f"Attempting to create text overlay with font size: {font_size}")
    font = get_font(font_size)

    # Verify font size
    test_text = "Test"
    bbox = draw.textbbox((0, 0), test_text, font=font)
    actual_height = bbox[3] - bbox[1]
    print(f"Requested font size: {font_size}, Actual text height: {actual_height}")

    width, height = img_size
    margin = 100  # Adjusted margin for better text fit
    max_width = width - (2 * margin)

    words = text.split()
    lines = []
    current_line = []
    current_width = 0

    for word in words:
        word_width = draw.textlength(word + " ", font=font)
        if current_width + word_width <= max_width:
            current_line.append(word)
            current_width += word_width
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_width = word_width

    if current_line:
        lines.append(" ".join(current_line))

    return lines, font


def add_text_to_image(image_path, roast_text):
    try:
        # Open the original image
        img = Image.open(image_path).convert('RGBA')
        
        # Resize image to standard width
        img = resize_image(img, STANDARD_WIDTH)
        width, height = img.size
        print(f"Image size after resize: {width}x{height}")

        # Split text into main roast and hashtag
        main_text = roast_text.split('#')[0].strip()
        hashtag = '#' + roast_text.split('#')[1].strip() if len(
            roast_text.split('#')) > 1 else '#LinkedInLunatic'

        # Create drawing object for calculating text size
        temp_draw = ImageDraw.Draw(img)

        # Adjusted font sizes for better fit
        main_font_size = 60  # Reduced from 200
        hashtag_font_size = 80  # Reduced from 220

        print(f"Using font sizes - Main: {main_font_size}, Hashtag: {hashtag_font_size}")

        # Get text lines and calculate required height for bottom section
        lines, font = create_text_overlay((width, height), temp_draw,
                                          main_text, main_font_size)
        line_height = int(main_font_size * 1.2)  # Reduced line height multiplier
        text_height = len(lines) * line_height
        
        # Calculate space needed
        vertical_padding = 60  # Reduced padding
        bottom_section_height = text_height + (vertical_padding * 2)

        # Create new image with extended height
        new_height = height + bottom_section_height
        new_img = Image.new('RGBA', (width, new_height), 'white')
        new_img.paste(img, (0, 0))

        # Create drawing object for new image
        draw = ImageDraw.Draw(new_img)

        # Draw main text in white section
        y_position = height + vertical_padding
        for line in lines:
            # Debug text positioning
            print(f"Drawing line at y_position: {y_position}")
            bbox = draw.textbbox((width/2, y_position), line, font=font, anchor="mm")
            print(f"Text bounding box: {bbox}")
            
            draw.text((width / 2, y_position),
                      line,
                      font=font,
                      fill='black',
                      anchor="mm")
            y_position += line_height

        # Add hashtag overlay on original image
        hashtag_font = get_font(hashtag_font_size)
        hashtag_y = height - int(height / 3)

        # Draw hashtag outline/shadow for better visibility
        outline_color = 'black'
        shadow_offset = 4  # Reduced shadow offset
        for offset_x in range(-shadow_offset, shadow_offset + 1):
            for offset_y in range(-shadow_offset, shadow_offset + 1):
                draw.text((width / 2 + offset_x, hashtag_y + offset_y),
                          hashtag,
                          font=hashtag_font,
                          fill=outline_color,
                          anchor="mm")

        # Draw the main hashtag in LinkedIn blue
        draw.text((width / 2, hashtag_y),
                  hashtag,
                  font=hashtag_font,
                  fill=LINKEDIN_BLUE,
                  anchor="mm")

        # Convert to RGB and save
        output_path = os.path.splitext(
            image_path)[0] + '_captioned' + os.path.splitext(image_path)[1]
        new_img = new_img.convert('RGB')
        new_img.save(output_path, quality=95)
        return output_path
    except Exception as e:
        print(f"Error adding text to image: {str(e)}")
        print(f"Error details:", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def analyze_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": SITE_URL,
                "X-Title": APP_NAME,
            },
            json={
                "model":
                "x-ai/grok-vision-beta",
                "messages": [{
                    "role":
                    "user",
                    "content": [{
                        "type":
                        "text",
                        "text":
                        "Generate a playful quote in the style of LinkedIn Lunatics, focusing on a professional LinkedIn profile picture. The quote should be humorous but lighthearted, poking fun at the person's appearance, demeanor, or any visible corporate elements (like their suit, tie, expression, or body language). Tie the quote to their professional persona or the stereotypical LinkedIn behavior (like 'networking', 'CEO vibes', 'always hustling'). Keep it fun, cheeky, and clever, but ensure it remains appropriate for a professional context. Aim for that LinkedIn Lunatics tone: witty and sarcastic, but never mean-spirited. Highlight how their appearance or attitude comes across in the photo and give it a humorous twist. Do this in 2-3 concise sentences. Don't use names. End the post with #linkedinlunatic"
                    }, {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }]
                }],
                "top_p":
                1,
                "temperature":
                1,
                "frequency_penalty":
                0,
                "presence_penalty":
                0,
                "repetition_penalty":
                1,
                "top_k":
                0,
            })

        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            print(f"Error from OpenRouter API: {response.status_code}")
            print(f"Response: {response.text}")
            return "I tried to roast this image, but the AI is having a coffee break! ☕"

    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
        return "I tried to roast this image, but it was already too hot to handle! 🔥"


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(file_path)
                print(f"File saved successfully at: {file_path}")

                # Store the file path in session for regeneration
                session['last_uploaded_image'] = file_path

                # Analyze the image
                roast = analyze_image(file_path)

                # Return JSON response with roast
                return jsonify({
                    'success': True,
                    'message': 'File uploaded successfully!',
                    'roast': roast
                })
            except Exception as e:
                print(f"Error saving file: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': 'Error uploading file',
                    'roast': None
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Allowed file types are png, jpg, jpeg, gif',
                'roast': None
            })

    return render_template('upload.html')


@app.route('/regenerate', methods=['POST'])
def regenerate_roast():
    if 'last_uploaded_image' not in session:
        return jsonify({
            'success': False,
            'message': 'No image found',
            'roast': None
        })

    try:
        roast = analyze_image(session['last_uploaded_image'])
        return jsonify({'success': True, 'roast': roast})
    except Exception as e:
        print(f"Error regenerating roast: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error generating new roast',
            'roast': None
        })


@app.route('/caption', methods=['POST'])
def caption_image():
    if 'last_uploaded_image' not in session:
        return jsonify({'success': False, 'message': 'No image found'})

    data = request.get_json()
    if not data or 'roast' not in data:
        return jsonify({'success': False, 'message': 'No roast text provided'})

    try:
        captioned_path = add_text_to_image(session['last_uploaded_image'],
                                           data['roast'])
        if captioned_path:
            # Get the filename only
            captioned_filename = os.path.basename(captioned_path)
            return jsonify({
                'success':
                True,
                'captioned_image':
                url_for('static', filename=f'pictures/{captioned_filename}')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error creating captioned image'
            })
    except Exception as e:
        print(f"Error in caption_image: {str(e)}")
        return jsonify({'success': False, 'message': 'Error processing image'})


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
