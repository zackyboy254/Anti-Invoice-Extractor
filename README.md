# 📄 Invoice Extractor Web App

A modern, fast, and user-friendly web application to extract structured data from PDF invoices (BMC and Pernod Ricard formats) and export them into a single, clean Excel file.

## ✨ Features
- **Batch Processing**: Upload multiple PDFs at once.
- **Auto-Detection**: The app identifies the invoice format automatically.
- **Manual Override**: Select a specific company format for better accuracy.
- **Session History**: Keep track of what you've processed in your current session.
- **Data Preview**: View extracted rows before downloading.
- **Selective Removal**: Remove individual files from your batch before generating the Excel file.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8 or higher.
- [Google Chrome](https://www.google.com/chrome/) (Recommended).

### 2. Installation
Clone this repository and install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the App
Start the server:
```bash
python -m uvicorn app:app --reload --port 8000
```
Then open your browser and go to: `http://127.0.0.1:8000`

## 🌐 Deployment (Online)

This app is production-ready! You can host it on platforms like **Render**, **Railway**, or **Heroku**.

### 1. Simple Deployment (Render)
1. Link your GitHub repo to [Render](https://render.com/).
2. Select **Web Service**.
3. Use these settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app`

### 2. Multi-User Support
The app uses a `session_id` logic to ensure that multiple users can process different batches of invoices at the same time without data mixing.

### 3. Monitoring (Logs)
All server-side activity (extractions, errors, downloads) is logged to `app.log`. On most hosting platforms, you can see these in the "Logs" tab of your dashboard.
