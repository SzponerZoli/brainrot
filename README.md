# Gen Alpha Content Generator

A modern web application that transforms regular text into Gen Alpha-style content with synchronized video, audio, and subtitles.

## Features

- 🎯 **AI-Powered Text Generation**
  - Converts standard text into Gen Alpha-style content
  - Uses Google's Gemini AI for natural language processing
  - Maintains original language and context while adding modern flair

- 🎨 **Dynamic Video Creation**
  - Creates vertical format videos (9:16 aspect ratio)
  - Supports multiple resolutions:
    - 1080p (1080x1920)
    - 900p (900x1600)
    - 720p (720x1280)
  - Professional video encoding with H264

- 🗣️ **Advanced Text-to-Speech**
  - OpenAI's TTS technology
  - Multiple voice options:
    - Alloy (Balanced)
    - Echo (Male)
    - Fable (British)
    - Onyx (Deep Male)
    - Nova (Female)
    - Shimmer (Clear Female)

- 📝 **Automatic Subtitle Generation**
  - Uses OpenAI Whisper for precise audio transcription
  - Synchronized SRT subtitle generation
  - Smart text chunking for optimal readability

- 🎨 **Modern UI/UX**
  - Responsive design
  - Real-time progress tracking and live log viewing (WIP)
  - Background video support

## Prerequisites

```bash
# Required Python version
Python 3.8+

# Required system packages
ffmpeg

# Required API keys
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SzponerZoli/brainrot.git
cd brainrot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Add background video:
```bash
# Place your background video in:
static/background_video.mp4
```

## Usage

1. Start the server:
```bash
python main.py
```

2. Open in browser:
```
http://localhost:5000
```

3. Generate content:
   - Enter your text
   - Click "Generate Text"
   - Edit the generated text if needed
   - Select video resolution and voice
   - Click "Create Video"

## Technical Details

### Video Processing Pipeline

1. **Text Generation**
   - Input text processed by Gemini AI
   - Optimized for Gen Alpha style and tone

2. **Audio Generation**
   - Text converted to speech using OpenAI's TTS
   - Multiple voice options with different characteristics

3. **Subtitle Creation**
   - Audio transcribed using Whisper API
   - Chunked into readable segments
   - Synchronized with audio timing

4. **Video Assembly**
   - Background video cropping and scaling
   - Audio overlay
   - Subtitle burning with customizable styling
   - Final encoding with quality optimization

### File Structure

```
brainrot/
├── main.py           # Main application file
├── templates/        # HTML templates
│   └── index.html   # Main UI template
├── static/          # Static assets
│   ├── styles/     # CSS files
│   └── background_video.mp4
└── temp_files/      # Temporary processing directory
```

## Contributing

1. Fork the repository
2. Commit your changes:
```bash
git commit -am 'Add some feature'
```
3. Push to the branch:
```bash
git push
```
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for TTS and Whisper APIs
- Google for Gemini AI
- FFmpeg for video processing
- Flask for web framework

<!-- GitAds-Verify: U25PRK9E713T26NWB1IW1ZAM4Q99TGC2 -->