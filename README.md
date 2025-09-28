# SyllaScan - AI-Powered Syllabus Analysis Dashboard

<img width=865 height=799 alt=Image src=https://github.com/user-attachments/assets/3388d497-6475-4ea4-ae47-e07474c89cb0 />

<img width=865 height=568 alt=Image src=https://github.com/user-attachments/assets/760d126e-6311-46e0-b675-483a0556940a />

## Overview

SyllaScan is an intelligent web application that transforms PDF syllabi into interactive dashboards. Upload your course syllabus and get instant access to key policies, assignment schedules, grading breakdowns, and an AI-powered Q&A system to quickly find answers to common questions.

## What it does

SyllaScan automatically processes your syllabus PDF and provides:
- **📋 Extracted FAQs**: Automatically identifies late work policies, attendance requirements, and course structure
- **📅 Schedule Visualization**: Interactive charts showing assignment distribution and cumulative grading weights by week  
- **🤖 AI Q&A System**: Ask natural language questions about your syllabus and get instant answers
- **📊 Grade Analysis**: Visual breakdown of how your final grade is distributed across assignments and weeks

## Features

### PDF Processing
- **OCR with Google Vision**: Converts PDF syllabi to searchable text with high accuracy
- **Smart Document Parsing**: Handles various syllabus formats and layouts
- **Large File Support**: Processes multi-page documents up to 25MB

### AI-Powered Analysis  
- **Automated FAQ Extraction**: Uses Gemini AI to identify and structure key policies
- **Natural Language Q&A**: Ask questions like "What happens if I'm late?" or "When is the final exam?"
- **Contextual Answers**: AI responses are grounded in your specific syllabus content

### Visual Analytics
- **Cumulative Grade Tracking**: See how your grade builds up week by week
- **Assignment Distribution**: Visualize workload across the semester
- **Weight Analysis**: Understand the relative importance of different assessments

### Student-Focused Design
- **Instant Access**: No need to dig through lengthy PDFs for basic information
- **Mobile Responsive**: Works on all devices for on-the-go access
- **Session Persistence**: Your syllabus data stays loaded between visits

## Installation & Setup

### Prerequisites
- Python 3.12+
- Google Cloud Platform account
- Gemini API key

### 1. Clone the Repository
```bash
git clone https://github.com/robtzou/SyllaScan.git
cd SyllaScan
```

### 2. Install Dependencies
```bash
# Using pip
pip install -r requirements.txt

# Or using uv (recommended)
uv sync
```

### 3. Set Up Google Cloud Services

#### Google Cloud Vision API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Cloud Vision API
4. Create a service account and download the JSON key
5. Set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
```

#### Gemini API
1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set the environment variable:
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### 4. Run the Application
```bash
# Development mode
python app.py

# Or with uv
uv run python app.py

# Production (using gunicorn)
gunicorn app:app
```

The app will be available at `http://localhost:8080`

## How to Use

### 1. Upload Your Syllabus
1. Open the web application in your browser
2. Click the **"Choose PDF file"** button
3. Select your course syllabus (PDF format, up to 25MB)
4. Click **"Upload & Analyze"**

The system will automatically:
- Extract text using OCR
- Parse policies and schedules with AI
- Generate visual analytics

### 2. Explore Your Dashboard

#### FAQ Section
- **Late Work Policy**: Automatically extracted penalty rules
- **Attendance Policy**: Requirements and consequences  
- **Course Structure**: Overview of assignments and evaluations

#### Visual Analytics
- **Cumulative Grade Chart**: Shows how your grade builds week by week
- **Assignment Distribution**: Bar chart of workload across the semester

#### Ask Questions
- Use the Q&A box to ask natural language questions
- Examples:
  - *"What happens if I submit homework late?"*
  - *"How much is the final exam worth?"*
  - *"When is the midterm?"*
  - *"What's the attendance policy?"*

### 3. Navigate Your Data
- All extracted information persists in your session
- Upload a new syllabus anytime to replace the current one
- Ask unlimited questions about the uploaded content

## How we built it

### Architecture Overview
```
PDF Upload → OCR Processing → AI Analysis → Web Dashboard
     ↓            ↓              ↓           ↓
   Flask      Google Vision   Gemini AI   Matplotlib
```

### Technology Stack

#### Frontend
- **HTML/CSS/JavaScript**: Modern responsive design with dark/light theme support
- **Chart.js Integration**: Interactive visualizations via Matplotlib-generated charts
- **Mobile-First Design**: Optimized for all screen sizes

#### Backend  
- **Flask**: Lightweight Python web framework handling routes and sessions
- **Flask-Session**: Filesystem-based session management for large data persistence
- **PyMuPDF**: PDF-to-image conversion for OCR preprocessing

#### AI & OCR Services
- **Google Cloud Vision**: High-accuracy OCR text extraction from PDF images
- **Gemini 2.5 Flash**: Advanced language model for:
  - Structured data extraction (FAQs, schedules)  
  - Natural language Q&A responses
  - Content summarization

#### Data Visualization
- **Matplotlib**: Generates assignment distribution and cumulative grade charts
- **Dynamic PNG Generation**: Real-time chart creation with proper scaling

### Key Features
- **Graceful Degradation**: Mock mode available when API keys aren't configured
- **Error Handling**: Comprehensive exception handling for all external services  
- **Session Management**: Large text data stored in temporary files vs. cookies
- **Security**: Proper CORS handling, file size limits, and input validation

## Configuration

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Your Google Gemini API key for AI processing |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | Path to Google Cloud service account JSON |
| `FLASK_SECRET_KEY` | No | Custom secret key (auto-generated if not set) |
| `PORT` | No | Port number (default: 8080) |
| `USE_MOCK` | No | Set to "1" to enable mock mode without API calls |

*Not required when `USE_MOCK=1`

### Mock Mode
For development or testing without API keys:
```bash
export USE_MOCK=1
python app.py
```

Mock mode provides realistic sample data to test the interface without external API calls.

### Docker Deployment
```bash
# Build the image
docker build -t syllascan .

# Run with environment variables
docker run -p 8080:8080 \
  -e GEMINI_API_KEY="your_key" \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/credentials.json" \
  -v /path/to/credentials.json:/app/credentials.json \
  syllascan
```

## Challenges we ran into

- **Google Cloud IAM Configuration**: Setting up service accounts and proper API permissions required careful navigation of GCP console
- **Large PDF Handling**: Managing memory efficiently for multi-page documents and implementing session-based storage for large OCR text
- **AI Response Consistency**: Fine-tuning prompts to ensure Gemini returns properly structured JSON for consistent data extraction
- **Chart Generation**: Creating dynamic matplotlib visualizations that render properly in web context with appropriate scaling

## What we're proud of

- **Rapid Development**: Built a fully functional AI-powered application with production-ready features
- **User-Centric Design**: Solved a real student problem with an intuitive, accessible interface
- **Robust Architecture**: Implemented proper error handling, session management, and graceful API failures
- **Smart AI Integration**: Effective prompt engineering for reliable structured data extraction from unstructured syllabi

## What we learned

- **API Integration**: Deep experience with Google Cloud services and managing multiple AI APIs
- **Session Management**: Techniques for handling large data persistence in web applications
- **Prompt Engineering**: Best practices for reliable structured output from generative AI models
- **Full-Stack Development**: End-to-end web application development with modern Python tooling

## What's next for SyllaScan

### Short Term
- **📅 Calendar Integration**: Export assignments directly to Google Calendar or Outlook
- **🚀 Performance**: Switch to Groq API for faster AI responses
- **📱 Mobile App**: Native iOS/Android applications for better mobile experience

### Long Term  
- **🤝 Multi-Class Support**: Manage multiple courses simultaneously
- **🎯 Smart Notifications**: Proactive reminders based on assignment due dates
- **� Grade Tracking**: Integration with actual grades to track progress against syllabus expectations
- **💰 Premium Features**: Advanced analytics and institutional licensing for universities

---

## Contributing

We welcome contributions! Please see our contributing guidelines for details on how to:
- Report bugs
- Suggest features  
- Submit pull requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you find SyllaScan helpful, please consider:
- ⭐ Starring this repository
- 🐛 Reporting issues
- 💡 Suggesting features
- 🤝 Contributing code

---
*Built with ❤️ for students everywhere*
