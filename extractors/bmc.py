import re
import pdfplumber
from extractors.base import BaseExtractor

class BMCExtractor(BaseExtractor):
    """
    Parser for Biashara Merchant Company Ltd Invoices.
    """
    def __init__(self, pdf_source):
        super().__init__(pdf_source)
        self.company_name = "Biashara Merchant Company Ltd"

    def extract(self) -> list[dict]:
        with pdfplumber.open(self.pdf_source) as pdf:
            # Iterate through all pages in the PDF
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                # Specific parsing logic for BMC
                self._parse_page_text(text)
                
        return self.extracted_items

    def _parse_page_text(self, text: str):
        """
        Extracts BMC specific fields using regex and text layout rules.
        """
        lines = text.split('\n')
        
        # --- HEADER EXTRACTION ---
        customer_name = ""
        ship_to_name = "" # Often the same as customer name or listed below it
        order_number = ""
        date = ""
        
        # 1. Find Customer Name (Usually under "To:" or similar in BMC format)
        for i, line in enumerate(lines):
            if line.strip().startswith("To:"):
                # The next few lines usually contain the customer details
                # In the sample: "39702" -> "Majid Al Futtaim Hypermarkets"
                if i + 2 < len(lines):
                    customer_name = lines[i+2].strip()
                    ship_to_name = lines[i+3].strip() if i+3 < len(lines) else customer_name
                break
                
        # 2. Find Order Number (Usually in a table header row: Account | Date | Order No | Delivery Note | Our Reference)
        for i, line in enumerate(lines):
            if "Order No" in line and "Delivery Note" in line:
                if i + 1 < len(lines):
                    # Next line contains the values. We can split by spaces
                    vals = lines[i+1].split() # type: ignore
                    if len(vals) >= 3:
                        order_number = vals[2] # Typically the 3rd column
                break
                
        # --- LINE ITEM EXTRACTION ---
        # Look for the table headers
        parsing_items = False
        for line in lines:
            if "Item Code" in line and "Item Description" in line:
                parsing_items = True
                continue
                
            if parsing_items:
                # Stop parsing if we hit a blank line or a footer keyword like "Total"
                if not line.strip() or "Total" in line:
                    break
                    
                # A typical line: "244128 Grants Triple Wood 12x75cl 40.0 NR WRD TR GX 12.00 Bottles 2,234.48 15.36"
                # Regex to match the pattern: Code Description [Quantity] [Unit (e.g. Bottles)] [Tax] [Weight]
                
                # Match ending with: [Quantity] [Unit (Optional)] [Tax (Optional)] [Weight]
                # Regex: Qty(1) Unit(2, optional) Tax(3, optional) Weight(4)
                match = re.search(r'([\d\.\,]+)\s+([A-Za-z]*)\s*(?:([\d\,\.]+)\s+)?([\d\.\,]+)$', line.strip())
                if match:
                    qty = match.group(1)
                    unit = match.group(2)
                    tax = match.group(3) # Might be None
                    weight = match.group(4)
                    
                    # The rest is Code + Description
                    rest = line[:match.start()].strip() # type: ignore
                    parts = rest.split(' ', 1)
                    code = parts[0] if len(parts) > 0 else ""
                    desc = parts[1] if len(parts) > 1 else ""
                    
                    try:
                        qty_float = float(qty)
                        weight_float = float(weight)
                        
                        row = self._create_standard_row(
                            company_name=self.company_name,
                            ship_to_name=ship_to_name,
                            order_number=order_number,
                            customer_name=customer_name,
                            product_code=code,
                            product_description=desc,
                            cases=None, # BMC doesn't specify Cases explicitly in standard layout
                            units=qty_float,
                            uom=unit,
                            qty_ordered=qty_float,
                            weight=weight_float
                        )
                        self.extracted_items.append(row)
                        
                    except ValueError:
                        print(f"Failed to parse numbers in line: {line}")
