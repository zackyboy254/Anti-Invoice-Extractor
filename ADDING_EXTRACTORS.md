# 🚀 Adding a New Company Extractor

Follow these steps to add support for a new company's invoice format.

## 1. Create the Extractor Class
Create a new file in `extractors/` (e.g., `new_company.py`). Inherit from `BaseExtractor` and implement the `extract()` method.

```python
from extractors.base import BaseExtractor
import pdfplumber

class NewCompanyExtractor(BaseExtractor):
    def __init__(self, pdf_source):
        super().__init__(pdf_source)
        self.company_name = "New Company Name"

    def extract(self) -> list[dict]:
        with pdfplumber.open(self.pdf_source) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # Your custom parsing logic here...
                # Iterate rows and use self._create_standard_row(...)
                # self.extracted_items.append(row)
        return self.extracted_items
```

## 2. Register in the Factory
Open `extractors/factory.py` and:
- Import your new class.
- Add an `elif` in `get_extractor` to detect a unique keyword in the PDF text.

```python
elif "unique keyword" in text_lower:
    return NewCompanyExtractor(pdf_source)
```

## 3. Register in the Web App
Open `app.py` and add your class to the `COMPANY_EXTRACTORS` dictionary:

```python
COMPANY_EXTRACTORS = {
    "bmc": BMCExtractor,
    "pernod": PernodExtractor,
    "new_company": NewCompanyExtractor, # Add here
}
```

## 4. Update the Frontend
Open `static/app.js` and add the label to `COMPANY_LABELS`:

```javascript
const COMPANY_LABELS = {
    "bmc": "Biashara Merchant",
    "pernod": "Pernod Ricard",
    "new_company": "New Company Name", // Add here
};
```

---
### 💡 Pro Tip
Check `bmc.py` or `pernod.py` for examples of regex-based and layout-based parsing!
