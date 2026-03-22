import os
import json
import logging

logger = logging.getLogger("InvoiceExtractor")

class AIOnboardingService:
    """
    Handles the generation of JSON extraction rules using AI.
    """
    
    @staticmethod
    async def generate_template(pdf_text: str, company_name: str) -> dict:
        """
        Sends PDF text to AI and returns a structured JSON template.
        In a production environment, this would call Gemini 1.5 Flash.
        """
        
        # MOCK PROMPT (Conceptual)
        # "Analyze this invoice text and identify the regex patterns for:
        #  - Order number, Date, Customer Name
        #  - Line items (Code, Description, Qty, Unit, Weight)
        # Return only a JSON object adhering to our Template Schema."
        
        logger.info(f"Generating AI template for: {company_name}")
        
        # Example of what the AI would generate:
        mock_template = {
            "company_name": company_name,
            "company_key": company_name.lower().replace(" ", "_"),
            "detection_keywords": [company_name, "Tax Invoice"],
            "header_rules": {
                "order_number": r"Order No:\s*(\w+)",
                "date": r"Date:\s*([\d/]+)",
                "customer_name": r"Customer:\s*(.*)"
            },
            "line_item_rules": {
                "header_trigger": "Description",
                "stop_trigger": "Total",
                "row_pattern": r"^(\w+)\s+(.*?)\s+([\d\.]+)\s+([A-Za-z]+)\s+([\d\.]+)$",
                "column_map": {
                    "product_code": 1,
                    "product_description": 2,
                    "units": 3,
                    "uom": 4,
                    "weight": 5
                }
            }
        }
        
        return mock_template

    @staticmethod
    def save_template(template: dict):
        """Saves the generated template to the company_rules directory."""
        rules_dir = os.path.join(os.getcwd(), "extractors", "company_rules")
        os.makedirs(rules_dir, exist_ok=True)
        
        filename = f"{template['company_key']}.json"
        filepath = os.path.join(rules_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(template, f, indent=4)
        
        logger.info(f"Saved new template: {filepath}")
        return filepath
