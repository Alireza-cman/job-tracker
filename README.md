# Job Application Tracker

AI-powered job application tracker with Streamlit UI and LangGraph backend.

## Quick Start

### 1. Install

```bash
cd JobApply
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file:

```
SECRET_KEY=your-32-char-secret-key
OPENAI_API_KEY=sk-your-openai-key
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` and create an account.

## Deployment (EC2)

```bash
git clone <repo> && cd JobApply
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export OPENAI_API_KEY=sk-xxx
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## Docker

```bash
docker build -t job-tracker .
docker run -d -p 8501:8501 \
  -e SECRET_KEY=xxx -e OPENAI_API_KEY=sk-xxx \
  -v $(pwd)/data:/app/data job-tracker
```

## Troubleshooting

- **SECRET_KEY error**: Set `SECRET_KEY` in `.env` or export it
- **URL fetch fails**: Use "Paste Text" mode instead
- **Reset database**: `rm -rf data/`
