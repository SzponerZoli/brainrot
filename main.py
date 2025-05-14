# main.py
import os
import subprocess
import uuid
import textwrap
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, g
import json
import time
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
app = Flask(__name__,
            template_folder='templates',  # Set template directory
            static_folder='static'  # Set static files directory
            )

progress_data = {'message': 'Initializing...', 'percentage': 0}

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate-text', methods=['POST'])
def generate_text():
    try:
        original_text = request.form.get('text')
        gen_alpha_text = rewrite_to_gen_alpha(original_text)

        return jsonify({
            'success': True,
            'original_text': original_text,
            'generated_text': gen_alpha_text
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/create-video', methods=['POST'])
def create_video_route():
    try:
        text = request.form.get('text')
        voice = request.form.get('voice')
        resolution = request.form.get('resolution', '1080p')

        update_progress("Generating audio...", 25)
        audio_path = generate_audio(text, voice)

        update_progress("Creating subtitles...", 50)
        subtitle_path = create_subtitles(text, audio_path)

        update_progress("Creating video...", 75)
        video_path = create_video(audio_path, subtitle_path, resolution)

        update_progress("Done!", 100)

        return jsonify({
            'success': True,
            'video_url': f'/download/{os.path.basename(video_path)}'
        })
    except Exception as e:
        update_progress("Error occurred. Please retry.", 0)
        return jsonify({'success': False, 'error': str(e)})


@app.route('/progress')
def progress():
    def generate():
        while True:
            data = {
                'message': progress_data.get('message', 'Initializing...'),
                'percentage': progress_data.get('percentage', 0)
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.5)  # Update every 0.5 seconds

    return Response(generate(), mimetype='text/event-stream')


def update_progress(message, percentage):
    """Update progress in global context"""
    with app.app_context():
        g.progress_message = message
        g.progress_percentage = percentage


def rewrite_to_gen_alpha(text):
    """Use Gemini to rewrite text in Gen Alpha style."""
    try:
        prompt = f"""
        Rewrite the following text in "Gen Alpha" style with no emojis in the language as the original text, which is:
        - Fast-paced and dynamic
        - Uses trendy expressions and pop culture references
        - Feels authentic to someone born after 2010
        - Energetic and engaging
        - be short like a youtube short video (max 180 words, 1 minute)
        - no emojis
        - in the language as the original text.
        - Use a friendly and relatable tone
        - Use simple and clear language

        Original text: {text}
        """

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)

        if response.text:
            return response.text.strip()
        else:
            raise Exception("No response generated")

    except Exception as e:
        print(f"Error in rewrite_to_gen_alpha: {str(e)}")
        raise Exception(f"Failed to generate text: {str(e)}")


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


def create_subtitles(text, audio_path):
    """Create a synchronized SRT subtitle file using OpenAI's STT for timing."""
    temp_dir = "temp_files"
    subtitle_path = os.path.join(temp_dir, f"{uuid.uuid4()}.srt")

    try:
        # Get audio duration
        audio_info = subprocess.check_output(
            ['ffprobe', '-i', audio_path, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=%s' % ("p=0")],
            universal_newlines=True
        ).strip()
        audio_duration = float(audio_info)

        # Use OpenAI's Whisper for timing
        with open(audio_path, 'rb') as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

        # Create chunks based on word timestamps
        chunks = []
        current_chunk = []
        current_start = None

        for segment in transcript.segments:
            if not current_start:
                current_start = segment.start

            current_chunk.append(segment.text)

            # Split chunks at natural breaks or when they get too long
            if (len(' '.join(current_chunk)) > 35 or
                    segment.end - current_start > 2.5 or  # max 2.5 seconds per chunk
                    '.' in segment.text or
                    '!' in segment.text or
                    '?' in segment.text):
                chunks.append({
                    'text': ' '.join(current_chunk).strip(),
                    'start': current_start,
                    'end': segment.end
                })
                current_chunk = []
                current_start = None

        # Write SRT file
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            for i, chunk in enumerate(chunks, 1):
                start_formatted = format_timestamp(chunk['start'])
                end_formatted = format_timestamp(chunk['end'])

                f.write(f"{i}\n")
                f.write(f"{start_formatted} --> {end_formatted}\n")
                f.write(f"{chunk['text']}\n\n")

        return subtitle_path

    except Exception as e:
        print(f"Error in create_subtitles: {str(e)}")
        raise Exception(f"Failed to create subtitles: {str(e)}")


def format_timestamp(seconds):
    """Format seconds to SRT timestamp (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds % 1) * 1000)
    seconds = int(seconds)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def create_video(audio_path, subtitle_path, resolution='1080p'):
    """Combine audio with background video and subtitles using FFmpeg."""
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)

    background_video = "static/background_video.mp4"
    output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")

    # Resolution mapping (9:16 aspect ratio)
    resolutions = {
        '720p': (720, 1280),
        '900p': (900, 1600),
        '1080p': (1080, 1920)
    }

    width, height = resolutions.get(resolution, resolutions['1080p'])
    bitrates = {
        '720p': '4000k',
        '900p': '5000k',
        '1080p': '6000k'
    }

    # Get audio duration
    audio_info = subprocess.check_output(
        ['ffprobe', '-i', audio_path, '-show_entries', 'format=duration',
         '-v', 'quiet', '-of', 'csv=%s' % ("p=0")],
        universal_newlines=True
    ).strip()

    audio_duration = float(audio_info)
    temp_video = os.path.join(temp_dir, f"temp_{uuid.uuid4()}.mp4")

    # Video encoding using VAAPI
    subprocess.run([
        'ffmpeg',
        '-i', background_video,  # Bemeneti videó
        '-i', audio_path,        # Bemeneti audio
        '-t', str(audio_duration), # Kivágás az audio hossza alapján
        '-filter_complex',
        f'[0:v]scale=-1:{height},crop={width}:{height},setsar=1:1[v]',  # Videó szűrők
        '-map', '[v]',
        '-map', '1:a',
        '-c:v', 'libx264',  # H264 kódolás CPU-val
        '-b:v', '6000k',    # Bitrate
        '-c:a', 'aac',      # Audio kodek
        temp_video
    ], check=True)

# Feliratok hozzáadása
    font_size = int(height * 0.005)
    margin_v = int(height * 0.03)

    subprocess.run([
        'ffmpeg',
        '-i', temp_video,
        '-vf',
        f"subtitles='{subtitle_path}':force_style='FontSize={font_size},PrimaryColour=&HFFFFFF&,OutlineColour=&AF2FFF&,Outline=2,Shadow=0,Alignment=2,MarginV={margin_v}'",  # Feliratok
        '-c:v', 'libx264',  # H264 kódolás
        '-b:v', '6000k',
        '-r', '25',
        '-c:a', 'copy',  # Audio változtatása nélkül
        output_path
    ], check=True)

        # Clean up temp file
    os.remove(temp_video)

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

    app.run(debug=False)
