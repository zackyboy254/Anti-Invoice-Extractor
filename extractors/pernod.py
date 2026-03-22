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
        with pdfplumber.open(self.pdf_source) as pdf:
            # We usually only need the first page, but we'll iterate just in case
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                self._parse_page_text(text)
                
        return self.extracted_items

    def _parse_page_text(self, text: str):
        """
        Extracts Pernod Ricard specific fields.
        """
        lines = text.split('\n')
        
        # --- HEADER EXTRACTION ---
        customer_name = ""
        ship_to_name = "" 
        order_number = ""
        
        for i, line in enumerate(lines):
            # 1. Customer Name and Ship To Name
            # The line looks like: Sold To: Quick Mart Limited Ship To: Quick Mart (Kilimani) Order Number: 25001484 SO 00471
            if line.strip().startswith("Sold To:"):
                # Handle everything in one line safely
                parts = line.split("Ship To:")
                customer_name = parts[0].replace("Sold To:", "").strip()
                if len(parts) > 1:
                    # Look for Order Number in the second part and split it out
                    ship_to_parts = parts[1].split("Order Number:")
                    ship_to_name = ship_to_parts[0].strip()
                    if len(ship_to_parts) > 1:
                        order_number = ship_to_parts[1].strip().split()[0]
                else:
                    ship_to_name = customer_name
                    
            # Fallback if Order Number is on its own line
            elif "Order Number:" in line and not order_number:
                order_number = line.split("Order Number:")[1].strip().split()[0]
                
        # --- LINE ITEM EXTRACTION ---
        # Look for the table headers
        parsing_items = False
        
        # We need a buffer because the description can span multiple lines!
        current_item = {}
        
        for i, line in enumerate(lines):
            try:
                if "2nd Item Number" in line and "Descriptions" in line:
                    parsing_items = True
                    continue
                    
                if parsing_items:
                    # Stop parsing if we hit a blank line or a footer keyword like "Total"
                    if not line.strip() or "Total for Order" in line:
                        break
                        
                    # A typical line 1: "K101149 JAMESON BLACK BARREL 2 2 22.8000"
                    # A typical line 2: "6 X 75 CL + 2 GLASSES 40% CA" 
                    # Note: Because the text flows weirdly in columns, sometimes
                    # the first line has the item number, first line of desc, cases, qty ordered, weight
                    # And the second line has the rest of desc, units, UM
                    
                    # Regex logic: 
                    # If it starts with an Item Code (like K101149), it's a new item!
                    if re.match(r'^K\d+', line.strip()) or re.match(r'^\w{6,8}', line.strip()):
                        # Save the previous item if we have one
                        if current_item:
                            self._append_row(customer_name, ship_to_name, order_number, current_item)
                            
                        # Match: Code Description [Cases or Units (Optional)] [UM (Optional)] [Qty Ordered] [Weight]
                        # We match optionally the first number, then UM, then Qty, then Weight
                        match = re.search(r'(?:([\d\.]+)\s+)?([A-Za-z]*)\s*([\d\.]+)\s+([\d\.]+)$', line.strip())
                        
                        code = line.split()[0]
                        desc = ""
                        qty_ordered = None
                        weight = None
                        cases = None
                        units = None
                        um = None
                        
                        if match:
                            cases_or_units = match.group(1)
                            um = match.group(2)
                            qty_ordered = float(match.group(3))
                            weight = float(match.group(4))
                            
                            if cases_or_units:
                                if um.upper() == "CA":
                                    cases = float(cases_or_units)
                                else:
                                    units = float(cases_or_units)
                                    
                            desc = line[len(code):match.start()].strip()
                                
                        current_item = {
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
                        # Match ending with: [Units] [UM] or just [UM] 
                        if not current_item:
                            continue
                            
                        # Look for something like "6.00 EA" or "CA" at the very end of the string
                        end_match = re.search(r'(?:([\d\.]+)\s+)?([A-Za-z]+)$', line.strip())
                        
                        # Only apply the unit logic if we are sure it looks like a unit continuation (less than 12 chars usually)
                        # Or if we know UM is missing from the parent
                        if end_match and not current_item["um"] and len(line.strip().split()) <= 3:
                            cases_or_units = end_match.group(1)
                            um = end_match.group(2)
                            
                            if cases_or_units:
                                if um.upper() == "CA":
                                    current_item["cases"] = float(cases_or_units)
                                else:
                                    current_item["units"] = float(cases_or_units)
                            
                            current_item["um"] = um
                            
                            # Remaining text is more description
                            more_desc = line[:end_match.start()].strip()
                            if more_desc:
                                current_item["desc"] = str(current_item["desc"]) + " " + more_desc
                        else:
                            # It's entirely description
                            current_item["desc"] = str(current_item["desc"]) + " " + line.strip()
            except Exception as e:
                print(f"Failed parsing line: {line}. Error: {e}")
                
        # Append the last item
        if current_item:
            self._append_row(customer_name, ship_to_name, order_number, current_item)
            
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
