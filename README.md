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

## 🛠️ Adding New Companies
This project is designed to be easily extensible. If you want to add a new invoice structure, check out the [ADDING_EXTRACTORS.md](ADDING_EXTRACTORS.md) guide.

## 🛡️ License
MIT
