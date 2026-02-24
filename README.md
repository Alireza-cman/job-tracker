# Job Application Tracker

A Streamlit-powered job application tracker with AI-driven extraction using LangGraph and OpenAI.

## Features

- **Smart Extraction**: Paste a URL or job description text, and the LLM extracts structured data (company, title, location, salary, requirements, etc.)
- **URL Fetching**: Automatically fetches and parses job posting pages (with graceful fallback to manual paste)
- **Application Management**: Track applications through various stages (Saved → Applied → Interviewing → Offer)
- **Search & Filter**: Find applications by status, company, or keywords
- **CSV Export**: Export all your applications for analysis
- **Notes**: Add personal notes to each application

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit UI                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ New App     │  │ List View   │  │ Details     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Pipeline                        │
│  route → fetch_url → clean_text → llm_extract → dedupe      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     SQLite Storage                           │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.10+
- OpenAI API key

### Setup

1. **Clone and navigate to the project:**

```bash
cd JobApply
```

2. **Create a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key-here
```

Or export directly:

```bash
export OPENAI_API_KEY=your-openai-api-key-here
```

## Usage

### Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### Pages

1. **Home** (`app.py`): Overview and quick stats
2. **New Application** (`pages/1_new_application.py`): Add new job applications
3. **Applications** (`pages/2_applications.py`): View, filter, and export applications
4. **Details** (`pages/3_details.py`): View/edit individual applications

### Adding a Job Application

1. Go to "New Application" page
2. Choose input mode:
   - **URL**: Paste a job posting URL (the system will fetch and extract text)
   - **Paste Text**: Directly paste the job description
3. Click "Extract" to run the AI extraction
4. Review and edit the extracted fields
5. Set initial status and click "Save"

### Test Fixtures

Sample job postings are provided in `tests/fixtures/` for testing:

- `sample_swe.txt` - Software Engineer job posting
- `sample_pm.txt` - Product Manager job posting

## Project Structure

```
JobApply/
├── app.py                      # Main Streamlit entry point
├── pages/
│   ├── 1_new_application.py    # Add new applications
│   ├── 2_applications.py       # List and filter applications
│   └── 3_details.py            # View/edit single application
├── backend/
│   ├── __init__.py
│   ├── models.py               # Pydantic schemas
│   ├── database.py             # SQLite operations
│   ├── nodes.py                # LangGraph pipeline nodes
│   ├── pipeline.py             # LangGraph graph definition
│   └── export.py               # CSV export
├── tests/
│   └── fixtures/               # Sample job postings
├── data/                       # SQLite database (auto-created)
├── requirements.txt
├── .env                        # Environment variables (create this)
└── README.md
```

## Deployment

### Local Deployment

Just run `streamlit run app.py` as described above.

### Cloud Deployment (Streamlit Cloud)

1. Push your code to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add `OPENAI_API_KEY` as a secret in the Streamlit Cloud settings
5. Deploy!

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:

```bash
docker build -t job-tracker .
docker run -p 8501:8501 -e OPENAI_API_KEY=your-key job-tracker
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key for LLM extraction |

### LLM Model

The default model is `gpt-4o-mini`. To change it, edit `backend/nodes.py`:

```python
llm = ChatOpenAI(
    model="gpt-4o",  # or "gpt-3.5-turbo" for lower cost
    temperature=0,
    api_key=api_key,
)
```

## Troubleshooting

### URL Fetch Fails

Some job sites block automated requests. If you see a fetch error:
1. The UI will prompt you to switch to "Paste Text" mode
2. Manually copy the job description from the website
3. Paste it into the text area

### "OPENAI_API_KEY not set" Error

Make sure you have:
1. Created a `.env` file with your API key, OR
2. Exported the environment variable in your terminal

### Database Issues

The SQLite database is stored in `data/applications.db`. To reset:

```bash
rm -rf data/
```

The database will be recreated on the next run.

## License

MIT License - feel free to use and modify as needed.
