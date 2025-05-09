# Apollo People Finder

A Streamlit app that helps find and verify professional email addresses using Apollo.io and MillionVerifier APIs.

## Features

- Upload company data (CSV with website URLs)
- Search for professionals by job titles
- Find email addresses using Apollo.io
- Verify email addresses using MillionVerifier
- Download results (all or verified only)

## Setup

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run streamlit_app.py
```

## Required API Keys

- Apollo.io API key
- MillionVerifier API key

## Input CSV Format

Your CSV should include one of these columns:
- company_web_url
- comp_web_url

## Usage

1. Upload your company data CSV
2. Enter your API keys
3. Enter job titles (one per line or comma-separated)
4. Click "Find People and Verify Emails"
5. Download results (all or verified only) 