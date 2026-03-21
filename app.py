from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import io
import time
from datetime import datetime
from typing import Optional

from extractors.factory import ExtractorFactory
from extractors.bmc import BMCExtractor
from extractors.pernod import PernodExtractor
from utils.web_excel_writer import WebExcelWriter

app = FastAPI(title="Invoice Extractor UI")

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global state – fine for a single-user local web app
current_excel_writer = None

# Map frontend company keys → extractor classes
COMPANY_EXTRACTORS = {
    "bmc":    BMCExtractor,
    "pernod": PernodExtractor,
}

@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """Serves the main single-page application."""
    global current_excel_writer
    current_excel_writer = WebExcelWriter()
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/reset")
async def reset_backend():
    """Resets the in-memory excel writer for a fresh batch."""
    global current_excel_writer
    current_excel_writer = WebExcelWriter()
    return {"status": "success", "message": "Backend reset successful"}


@app.post("/process")
async def process_file(
    file: UploadFile = File(...),
    company: Optional[str] = Form(None),   # "bmc" | "pernod" from the dropdown
    file_id: str = Form(...),              # Frontend-generated unique ID
):
    """
    Processes a single PDF file, extracts data, and appends it to the 
    Excel buffer with a tracking file_id.
    """
    global current_excel_writer
    if current_excel_writer is None:
        current_excel_writer = WebExcelWriter()

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
        current_excel_writer.append_data(
            extracted_data, 
            file_id=file_id, 
            sheet_name=extractor.company_name
        )

        time.sleep(0.5)  # keeps the progress bar from blinking too fast

        return {
            "status":  "success",
            "message": f"Parsed {len(extracted_data)} line(s)",
            "company": extractor.company_name,
            "extracted_data": extracted_data
        }

    except Exception as e:
        print(f"Error processing {file.filename}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/remove-file")
async def remove_file_data(file_id: str = Form(...)):
    """
    Removes data associated with a specific file_id from the Excel buffer.
    """
    global current_excel_writer
    if current_excel_writer:
        current_excel_writer.remove_file_data(file_id)
    return {"status": "success"}


@app.get("/download")
async def download_excel(company: Optional[str] = None):
    """Returns the compiled Excel file with a dynamic filename based on company."""
    global current_excel_writer
    if current_excel_writer is None:
        raise HTTPException(status_code=400, detail="No files have been processed yet.")

    excel_stream = current_excel_writer.get_excel_bytes()

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
