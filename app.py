from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import io
import time
import logging
import uuid
from datetime import datetime
from typing import Optional

from extractors.factory import ExtractorFactory
from extractors.bmc import BMCExtractor
from extractors.pernod import PernodExtractor
from utils.web_excel_writer import WebExcelWriter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InvoiceExtractor")

app = FastAPI(title="Invoice Extractor UI")

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global session store – maps session_id -> WebExcelWriter instance
SESSION_STORES: dict[str, WebExcelWriter] = {}

def get_session_writer(session_id: str) -> WebExcelWriter:
    """Helper to retrieve or create a writer for a specific session."""
    if session_id not in SESSION_STORES:
        SESSION_STORES[session_id] = WebExcelWriter()
        logger.info(f"Created new session store: {session_id}")
    return SESSION_STORES[session_id]

# Map frontend company keys → extractor classes
COMPANY_EXTRACTORS = {
    "bmc":    BMCExtractor,
    "pernod": PernodExtractor,
}

@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """Serves the main single-page application with a unique session ID."""
    session_id = str(uuid.uuid4())
    return templates.TemplateResponse("index.html", {
        "request": request,
        "session_id": session_id
    })


@app.post("/reset")
async def reset_backend(session_id: str = Form(...)):
    """Resets the in-memory excel writer for a specific session."""
    SESSION_STORES.pop(session_id, None)
    logger.info(f"Reset session store: {session_id}")
    return {"status": "success", "message": "Backend reset successful"}


@app.post("/process")
async def process_file(
    file: UploadFile = File(...),
    company: Optional[str] = Form(None),   # "bmc" | "pernod" from the dropdown
    file_id: str = Form(...),              # Frontend-generated unique ID for line removal
    session_id: str = Form(...),           # Unique browser session ID
):
    """
    Processes a single PDF file, extracts data, and appends it to the 
    Excel buffer for the specific session.
    """
    writer = get_session_writer(session_id)
    logger.info(f"[{session_id}] Processing file: {file.filename} (Company: {company or 'Auto'})")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        contents  = await file.read()
        pdf_source = io.BytesIO(contents)

        # Use explicit company choice when available, otherwise auto-detect
        if company and company in COMPANY_EXTRACTORS:
            extractor = COMPANY_EXTRACTORS[company](pdf_source)
            print(f"Using selected extractor: {company} for {file.filename}")
        else:
            extractor = ExtractorFactory.get_extractor(pdf_source)

        extracted_data = extractor.extract()

        if not extracted_data:
            raise ValueError("No item rows could be extracted from this PDF.")

        # Store in buffer with tracking ID
        writer.append_data(
            extracted_data, 
            file_id=file_id, 
            sheet_name=extractor.company_name
        )

        logger.info(f"[{session_id}] Successfully parsed {len(extracted_data)} lines from {file.filename}")
        time.sleep(0.5)  # keeps the progress bar from blinking too fast

        return {
            "status":  "success",
            "message": f"Parsed {len(extracted_data)} line(s)",
            "company": extractor.company_name,
            "extracted_data": extracted_data
        }

    except Exception as e:
        logger.error(f"[{session_id}] Error processing {file.filename}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/remove-file")
async def remove_file_data(file_id: str = Form(...), session_id: str = Form(...)):
    """
    Removes data associated with a specific file_id from the session's Excel buffer.
    """
    if session_id in SESSION_STORES:
        SESSION_STORES[session_id].remove_file_data(file_id)
        logger.info(f"[{session_id}] Removed file data for ID: {file_id}")
    return {"status": "success"}


@app.get("/download")
async def download_excel(session_id: str, company: Optional[str] = None):
    """Returns the compiled Excel file for the specific session."""
    if session_id not in SESSION_STORES:
        logger.warning(f"Download attempt failed. Session not found: {session_id}")
        raise HTTPException(status_code=400, detail="No files have been processed in this session.")

    writer = SESSION_STORES[session_id]
    excel_stream = writer.get_excel_bytes()
    logger.info(f"[{session_id}] Generating download for company prefix: {company or 'Batch'}")

    # Determine filename prefix
    prefix = "Invoices"
    if company:
        # Sanitize prefix (alphanumeric and underscores only)
        prefix = "".join(c if c.isalnum() else "_" for c in company).strip("_")
        if not prefix: prefix = "Invoices"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_Extracted_{timestamp}.xlsx"

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
