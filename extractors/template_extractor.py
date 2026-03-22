import re
import json
import pdfplumber
from extractors.base import BaseExtractor

class TemplateExtractor(BaseExtractor):
    """
    A generic extractor that uses a JSON 'Rule Set' to parse invoices.
    This allows adding new companies without writing new Python code.
    """
    def __init__(self, pdf_source, template_path: str):
        super().__init__(pdf_source)
        with open(template_path, 'r') as f:
            self.rules = json.load(f)
        
        self.company_name = self.rules.get("company_name", "Unknown Company")
        self.company_key = self.rules.get("company_key", self.company_name.lower().replace(" ", "_"))

    def extract(self) -> list[dict]:
        with pdfplumber.open(self.pdf_source) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                self._parse_page_text(text)
                
        return self.extracted_items

    def _parse_page_text(self, text: str):
        lines = text.split('\n')
        
        # --- HEADER EXTRACTION ---
        header_vals = {}
        for field, pattern in self.rules.get("header_rules", {}).items():
            match = re.search(pattern, text)
            header_vals[field] = match.group(1).strip() if match else ""

        # --- LINE ITEM EXTRACTION ---
        line_rules = self.rules.get("line_item_rules", {})
        header_trigger = line_rules.get("header_trigger")
        stop_trigger = line_rules.get("stop_trigger")
        row_pattern = line_rules.get("row_pattern")
        column_map = line_rules.get("column_map", {})

        parsing_items = False
        block_lines = []
        for line in lines:
            if header_trigger and header_trigger in line:
                parsing_items = True
                continue
                
            if parsing_items or not header_trigger:
                if stop_trigger and stop_trigger in line:
                    break
                # Only add non-empty lines to block if they have content, or keep all to maintain structure
                block_lines.append(line)
        
        block_text = '\n'.join(block_lines)

        # Find all matches in the concatenated block
        if row_pattern:
            for match in re.finditer(row_pattern, block_text, re.MULTILINE):
                groups = match.groups()
                
                # Map regex groups to standard fields
                row_data = {}
                for field, group_idx in column_map.items():
                    # group_idx is 1-based as per usual regex convention in JSON
                    try:
                        val = groups[int(group_idx) - 1]
                        # Try to clean numeric values
                        if field in ["units", "qty_ordered", "weight", "cases"] and val is not None:
                            # Handle string cleaning before float parsing
                            clean_val = val.replace(',', '').strip()
                            if clean_val:
                                val = float(clean_val)
                            else:
                                val = 0.0
                        row_data[field] = val
                    except (IndexError, ValueError, TypeError):
                        row_data[field] = None

                # Create standard row
                row = self._create_standard_row(
                    company_name=self.company_name,
                    ship_to_name=header_vals.get("ship_to_name", ""),
                    order_number=header_vals.get("order_number", ""),
                    customer_name=header_vals.get("customer_name", ""),
                    product_code=row_data.get("product_code", ""),
                    product_description=row_data.get("product_description", ""),
                    cases=row_data.get("cases"),
                    units=row_data.get("units"),
                    uom=row_data.get("uom", ""),
                    qty_ordered=row_data.get("qty_ordered"),
                    weight=row_data.get("weight")
                )
                self.extracted_items.append(row)
