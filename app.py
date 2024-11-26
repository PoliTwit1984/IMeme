from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, jsonify, session
import os
from werkzeug.utils import secure_filename
import requests
import json
import base64
from PIL import Image, ImageDraw, ImageFont, ImageColor
import textwrap
from PIL import ImageEnhance

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# OpenRouter configuration
OPENROUTER_API_KEY = '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'
SITE_URL = 'http://localhost:5000'
APP_NAME = 'IMeme'

# Ensure upload folder exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'pictures')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

LINKEDIN_BLUE = "#0077B5"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_text_overlay(img_size, draw, text, font_size, font_path=None):
    try:
        font = ImageFont.truetype("Arial Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    width, height = img_size
    margin = 40
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
        width, height = img.size
        
        # Split text into main roast and hashtag
        main_text = roast_text.split('#')[0].strip()
        hashtag = '#' + roast_text.split('#')[1].strip() if len(roast_text.split('#')) > 1 else '#LinkedInLunatic'

        # Create drawing object for calculating text size
        temp_draw = ImageDraw.Draw(img)
        
        # Calculate font sizes
        main_font_size = int(height/20)
        hashtag_font_size = int(height/15)  # Increased hashtag size
        
        # Get text lines and calculate required height for bottom section
        lines, font = create_text_overlay((width, height), temp_draw, main_text, main_font_size)
        line_height = int(main_font_size * 1.5)
        text_height = len(lines) * line_height
        bottom_section_height = text_height + 180  # Increased padding significantly
        
        # Create new image with extended height
        new_height = height + bottom_section_height
        new_img = Image.new('RGBA', (width, new_height), 'white')
        new_img.paste(img, (0, 0))
        
        # Create drawing object for new image
        draw = ImageDraw.Draw(new_img)
        
        # Draw main text in white section with more padding from the top
        y_position = height + 100  # Increased top padding significantly
        for line in lines:
            draw.text(
                (width/2, y_position),
                line,
                font=font,
                fill='black',
                anchor="mm"
            )
            y_position += line_height

        # Add hashtag overlay on original image - positioned higher up
        try:
            hashtag_font = ImageFont.truetype("Arial Bold.ttf", hashtag_font_size)
        except:
            hashtag_font = ImageFont.load_default()
        
        # Position hashtag higher up from the bottom with more space
        hashtag_y = height - int(height/4)  # Moved hashtag up significantly
        
        # Draw hashtag outline/shadow
        outline_color = 'black'
        shadow_offset = int(hashtag_font_size/15)
        for offset_x in range(-shadow_offset, shadow_offset + 1):
            for offset_y in range(-shadow_offset, shadow_offset + 1):
                draw.text(
                    (width/2 + offset_x, hashtag_y + offset_y),
                    hashtag,
                    font=hashtag_font,
                    fill=outline_color,
                    anchor="mm"
                )
        
        # Draw the main hashtag in LinkedIn blue
        draw.text(
            (width/2, hashtag_y),
            hashtag,
            font=hashtag_font,
            fill=LINKEDIN_BLUE,
            anchor="mm"
        )
        
        # Convert to RGB and save
        output_path = os.path.splitext(image_path)[0] + '_captioned' + os.path.splitext(image_path)[1]
        new_img = new_img.convert('RGB')
        new_img.save(output_path, quality=95)
        return output_path
    except Exception as e:
        print(f"Error adding text to image: {str(e)}")
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
                "model": "x-ai/grok-vision-beta",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Write a lighthearted roast for this person, using a description of their appearance or demeanor to imagine them as a LinkedIn Lunatic. Focus on exaggerated professional humblebrags, unnecessary life metaphors, and over-the-top self-congratulatory storytelling, tying it back to their looks or personality traits for a tailored roast. Do this in 2-3 concise sentences. End the post with #linkedinlunatic"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "top_p": 1,
                "temperature": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "repetition_penalty": 1,
                "top_k": 0,
            }
        )
        
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
        return jsonify({
            'success': True,
            'roast': roast
        })
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
        return jsonify({
            'success': False,
            'message': 'No image found'
        })
    
    data = request.get_json()
    if not data or 'roast' not in data:
        return jsonify({
            'success': False,
            'message': 'No roast text provided'
        })
    
    try:
        captioned_path = add_text_to_image(session['last_uploaded_image'], data['roast'])
        if captioned_path:
            # Get the filename only
            captioned_filename = os.path.basename(captioned_path)
            return jsonify({
                'success': True,
                'captioned_image': url_for('static', filename=f'pictures/{captioned_filename}')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error creating captioned image'
            })
    except Exception as e:
        print(f"Error in caption_image: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error processing image'
        })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    print(f"Upload folder is set to: {UPLOAD_FOLDER}")
    app.run(debug=True)
