# main.py
import os
import subprocess
import uuid
import textwrap
from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
from google import generativeai as genai
from dotenv import load_dotenv
import openai
import tempfile
import shutil

# Load environment variables
load_dotenv()

# Initialize APIs
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__, template_folder='webui', static_folder='static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_content():
    try:
        # Get form data
        original_text = request.form.get('text')
        voice = request.form.get('voice')
        
        # Rewrite text in Gen Alpha style using Gemini
        gen_alpha_text = rewrite_to_gen_alpha(original_text)
        
        # Make sure the text can be spoken in about one minute
        shortened_text = shorten_for_one_minute(gen_alpha_text)
        
        # Generate audio using OpenAI TTS
        audio_path = generate_audio(shortened_text, voice)
        
        # Create subtitles file
        subtitle_path = create_subtitles(shortened_text)
        
        # Create video with audio and subtitles
        video_path = create_video(audio_path, subtitle_path)
        
        # Return paths for frontend to use
        return jsonify({
            'success': True,
            'original_text': original_text,
            'gen_alpha_text': shortened_text,
            'video_url': f'/download/{os.path.basename(video_path)}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def rewrite_to_gen_alpha(text):
    """Use Gemini 2.0 Flash Lite to rewrite text in Gen Alpha style."""
    prompt = f"""
    Rewrite the following text in "Gen Alpha" style, which is:
    - Fast-paced and dynamic
    - Uses trendy expressions and pop culture references
    - Includes emojis
    - Feels authentic to someone born after 2010
    - Energetic and engaging
    
    Original text: {text}
    
    Gen Alpha version:
    """
    
    # Create and use the Gemini model directly
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    response = model.generate_content(prompt)
    
    return response.text

def shorten_for_one_minute(text):
    """Ensure text can be spoken in about one minute (approx 150-180 words)"""
    words = text.split()
    if len(words) > 180:
        shortened = ' '.join(words[:175])
        # Try to end at a sensible punctuation
        for punct in ['.', '!', '?', ';']:
            last_punct = shortened.rfind(punct)
            if last_punct > len(shortened) * 0.8:  # If it's near the end
                return shortened[:last_punct+1]
        return shortened
    return text

def generate_audio(text, voice):
    """Generate audio from text using OpenAI's TTS API."""
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp3")
    
    response = openai.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text
    )
    
    with open(audio_path, "wb") as audio_file:
        audio_file.write(response.content)
    
    return audio_path

def create_subtitles(text):
    """Create a simple SRT subtitle file with better timing and shorter chunks."""
    temp_dir = "temp_files"
    subtitle_path = os.path.join(temp_dir, f"{uuid.uuid4()}.srt")
    
    # Split into smaller chunks (around 30-40 characters)
    chunks = []
    current = ""
    words = text.split()
    
    for word in words:
        if len(current) + len(word) < 35:
            current += " " + word if current else word
        else:
            if current:
                chunks.append(current.strip())
            current = word
    if current:
        chunks.append(current.strip())
    
    # Estimate timing: average speaking rate is about 150 words per minute
    # So approximately 0.4 seconds per word
    with open(subtitle_path, 'w', encoding='utf-8') as f:
        current_time = 0
        for i, chunk in enumerate(chunks):
            # Calculate duration based on number of words
            word_count = len(chunk.split())
            duration = word_count * 0.4  # seconds per word
            
            start_time = current_time
            end_time = current_time + duration
            
            # Format time as HH:MM:SS,mmm
            start_formatted = f"{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d},{int((start_time%1)*1000):03d}"
            end_formatted = f"{int(end_time//3600):02d}:{int((end_time%3600)//60):02d}:{int(end_time%60):02d},{int((end_time%1)*1000):03d}"
            
            f.write(f"{i+1}\n")
            f.write(f"{start_formatted} --> {end_formatted}\n")
            f.write(f"{chunk}\n\n")
            
            current_time = end_time + 0.1  # Add a small gap between subtitles
    
    return subtitle_path

def create_video(audio_path, subtitle_path):
    """Combine audio with background video and subtitles using FFmpeg."""
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    
    background_video = "static/background_video.mp4"
    output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
    
    # Get audio duration
    audio_info = subprocess.check_output(
        ['ffprobe', '-i', audio_path, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=%s' % ("p=0")],
        universal_newlines=True
    ).strip()
    
    audio_duration = float(audio_info)
    
    # Create video with FFmpeg - specify 9:16 aspect ratio
    # First create temporary video with subtitles
    temp_video = os.path.join(temp_dir, f"temp_{uuid.uuid4()}.mp4")
    
    # Crop/pad the background video to 9:16 aspect ratio
    subprocess.run([
        'ffmpeg', '-i', background_video, 
        '-i', audio_path,
        '-t', str(audio_duration),
        '-filter_complex', 
        '[0:v]scale=-1:1920,crop=1080:1920,setsar=1:1[v];[v][1:a]concat=n=1:v=1:a=1[outv][outa]',
        '-map', '[outv]', 
        '-map', '[outa]',
        '-c:v', 'libx264', 
        '-c:a', 'aac',
        temp_video
    ], check=True)
    
    # Add subtitles to the video with centered text and black outline
    subprocess.run([
        'ffmpeg', '-i', temp_video,
        '-vf', f"subtitles={subtitle_path}:force_style='"
               f"FontName=Noto Color Emoji,"
               f"FontSize=18,"
               f"PrimaryColour=&HFFFFFF,"  # White text (FFFFFF)
               f"OutlineColour=&H000000,"  # Black outline (000000)
               f"BorderStyle=3,"           # Outline + shadow
               f"Outline=2,"               # Outline thickness
               f"Shadow=0,"                # No shadow
               f"Alignment=2,"             # 2 = centered
               f"MarginV=70'"             # Vertical margin from bottom
        ,
        '-c:v', 'libx264',
        '-b:v', '6000k',
        '-r', '25',
        '-c:a', 'copy',
        output_path
    ], check=True)
    
    # Clean up temporary files
    if os.path.exists(temp_video):
        os.unlink(temp_video)
    
    return output_path

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated video."""
    return send_from_directory('temp_files', filename, as_attachment=True)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up temporary files."""
    try:
        temp_dir = "temp_files"
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('temp_files', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Check if background video exists, if not create a placeholder
    if not os.path.exists('static/background_video.mp4'):
        print("Warning: background_video.mp4 not found in static folder. Please add one.")
        
    app.run(debug=True)