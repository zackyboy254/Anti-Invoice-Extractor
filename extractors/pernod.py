import re
import pdfplumber
from extractors.base import BaseExtractor

class PernodExtractor(BaseExtractor):
    """
    Parser for Pernod Ricard Kenya Invoices (Pick Slips).
    """
    def __init__(self, pdf_source):
        super().__init__(pdf_source)
        self.company_name = "Pernod Ricard Kenya"

    def extract(self) -> list[dict]:
        self.customer_name = ""
        self.ship_to_name = "" 
        self.order_number = ""
        self.current_item = {}
        self.parsing_items = False

        with pdfplumber.open(self.pdf_source) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                self._parse_page_text(text)
                
        # Append the very last item across all pages
        if self.current_item:
            self._append_row(self.customer_name, self.ship_to_name, self.order_number, self.current_item)
            self.current_item = {}

        return self.extracted_items

    def _parse_page_text(self, text: str):
        """
        Extracts Pernod Ricard specific fields from a single page, maintaining item extraction state.
        """
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # 1. Customer Name and Ship To Name (header might repeat on page 2 but usually only once)
            if line.strip().startswith("Sold To:"):
                parts = line.split("Ship To:")
                self.customer_name = parts[0].replace("Sold To:", "").strip()
                if len(parts) > 1:
                    ship_to_parts = parts[1].split("Order Number:")
                    self.ship_to_name = ship_to_parts[0].strip()
                    if len(ship_to_parts) > 1:
                        self.order_number = ship_to_parts[1].strip().split()[0]
                else:
                    self.ship_to_name = self.customer_name
                    
            elif "Order Number:" in line and not self.order_number:
                self.order_number = line.split("Order Number:")[1].strip().split()[0]
                
            # 2. Page Header Skip Logic
            if "Pernod Ricard Kenya" in line or "SINGLE PICK SLIP" in line or "Pick Slip #" in line:
                self.parsing_items = False
                continue

            # 3. Triggers for starting items
            if ("2nd Item Number" in line and "Descriptions" in line) or ("Instruction" in line and re.search(r'\d{4}/\d{2}/\d{2}', line)) or ("Order Date" in line and "Promised" in line):
                # The actual items start soon after these. 
                self.parsing_items = True
                continue
                
            # Strict check for an item code (even if parsing_items is False, a definite hit should resume it)
            is_k_code = bool(re.match(r'^K\d{5,8}\b', line.strip()))
            # Only accept non-K alphanumeric codes if they look like a full item line with trailing quantity and weight numbers
            is_generic_code = bool(re.match(r'^[A-Z0-9]{6,12}\b', line.strip())) and bool(re.search(r'[\d\.,]+\s+[\d\.,]+$', line.strip())) and not line.strip().startswith("R56HQ")
            is_item_code = is_k_code or is_generic_code
            is_date_line = bool(re.search(r'\d{4}/\d{2}/\d{2}', line.strip()))
            
            if is_item_code and not is_date_line:
                self.parsing_items = True

            if self.parsing_items:
                # Stop parsing if we hit a footer keyword
                if "Total for Order" in line or "Picker" in line or "Pick Slip No:" in line or "*169" in line:
                    self.parsing_items = False
                    continue
                    
                if is_item_code and not is_date_line:
                    # Save the previous item
                    if self.current_item:
                        self._append_row(self.customer_name, self.ship_to_name, self.order_number, self.current_item)
                        
                    # Match: Code Description [Cases or Units] [UM] [Qty] [Weight]
                    # We regex search from the back of the string
                    match = re.search(r'(?:([\d\.,]+)\s+)?([A-Za-z]*)\s*([\d\.,]+)\s+([\d\.,]+)$', line.strip())
                    
                    code = line.split()[0]
                    desc = ""
                    qty_ordered = None
                    weight = None
                    cases = None
                    units = None
                    um = None
                    
                    if match:
                        try:
                            cases_or_units = match.group(1)
                            um = match.group(2)
                            
                            # Clean commas before float conversion
                            qty_str = match.group(3).replace(',', '')
                            wt_str = match.group(4).replace(',', '')
                            
                            qty_ordered = float(qty_str)
                            weight = float(wt_str)
                            
                            if cases_or_units:
                                cu_val = float(cases_or_units.replace(',', ''))
                                if um and um.upper() == "CA":
                                    cases = cu_val
                                else:
                                    units = cu_val
                                    
                            desc = line[len(code):match.start()].strip()
                        except ValueError:
                            desc = line[len(code):].strip()
                    else:
                        desc = line[len(code):].strip()
                            
                    self.current_item = {
                        "code": code,
                        "desc": desc,
                        "cases": cases,
                        "qty_ordered": qty_ordered,
                        "weight": weight,
                        "units": units,
                        "um": um
                    }
                else:
                    # Continuation line (Units, UM, more description)
                    if not self.current_item:
                        continue
                        
                    # Prevent headers/dates from leaking into the description across page boundaries
                    if is_date_line or "Transport" in line or "Instruction" in line or line.strip() == "":
                        continue
                        
                    # Some continuation lines have quantity updates at the end like "6.00 EA" or just "CA"
                    end_match = re.search(r'(?:([\d\.,]+)\s+)?([A-Za-z]{2})$', line.strip())
                    
                    # Only apply unit logic if it looks like a clean unit (e.g., "CA", "EA", "UM")
                    if end_match and not self.current_item.get("um") and len(line.strip().split()) <= 4:
                        try:
                            cases_or_units = end_match.group(1)
                            um = end_match.group(2)
                            
                            if cases_or_units:
                                cu_val = float(cases_or_units.replace(',', ''))
                                if um.upper() == "CA":
                                    self.current_item["cases"] = cu_val
                                else:
                                    self.current_item["units"] = cu_val
                            
                            self.current_item["um"] = um
                            
                            more_desc = line[:end_match.start()].strip()
                            if more_desc:
                                self.current_item["desc"] = str(self.current_item["desc"]) + " " + more_desc
                        except ValueError:
                            self.current_item["desc"] = str(self.current_item["desc"]) + " " + line.strip()
                    else:
                        # Append to description
                        added_text = line.strip()
                        if added_text:
                            self.current_item["desc"] = str(self.current_item.get("desc", "")) + " " + added_text
            
    def _append_row(self, customer_name, ship_to_name, order_number, item):
        row = self._create_standard_row(
            company_name=self.company_name,
            ship_to_name=ship_to_name,
            order_number=order_number,
            customer_name=customer_name,
            product_code=item.get("code"),
            product_description=item.get("desc"),
            cases=item.get("cases"),
            units=item.get("units"),
            uom=item.get("um"),
            qty_ordered=item.get("qty_ordered"),
            weight=item.get("weight")
        )
        self.extracted_items.append(row)
