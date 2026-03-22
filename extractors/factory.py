import pdfplumber
from extractors.base import BaseExtractor
from extractors.bmc import BMCExtractor
from extractors.pernod import PernodExtractor

class ExtractorFactory:
    """
    Factory class that determines which extractor to use based on the PDF content.
    """
    @staticmethod
    def get_extractor(pdf_source) -> BaseExtractor:
        """
        Reads the first page of the PDF and looks for identifying keywords
        to return the correct extractor instance.
        """
        try:
            with pdfplumber.open(pdf_source) as pdf:
                # Just check the first page to identify the vendor
                if len(pdf.pages) > 0:
                    text = pdf.pages[0].extract_text()
                    if not text:
                        raise ValueError(f"Could not extract any text from the provided PDF")
                        
                    text_lower = text.lower()
                    
                    # --- ADD NEW VENDORS HERE ---
                    # To add a new vendor format:
                    # 1. Look for a unique string in their invoice header
                    # 2. Add an elif statement below checking for that string
                    # 3. Return the new Extractor class you created
                    
                    import os
                    import json
                    from extractors.template_extractor import TemplateExtractor
                    
                    # 1. First, check for dynamic JSON templates in the company_rules folder
                    rules_dir = os.path.join(os.path.dirname(__file__), "company_rules")
                    if os.path.exists(rules_dir):
                        for filename in os.listdir(rules_dir):
                            if filename.endswith(".json"):
                                try:
                                    template_path = os.path.join(rules_dir, filename)
                                    with open(template_path, 'r') as f:
                                        rules = json.load(f)
                                    
                                    # Check if any detection keyword matches the PDF text
                                    keywords = rules.get("detection_keywords", [])
                                    if any(kw.lower() in text_lower for kw in keywords):
                                        print(f"Detected format via Template: {rules.get('company_name')}")
                                        return TemplateExtractor(pdf_source, template_path)
                                except Exception as e:
                                    print(f"Error loading template {filename}: {e}")

                    # 2. Fall back to hard-coded extractors
                    if "biashara merchant company" in text_lower or "bmc" in text_lower or "delivery note" in text_lower:
                        print(f"Detected format: Biashara Merchant Company")
                        return BMCExtractor(pdf_source)
                        
                    elif "pernod ricard" in text_lower or "pick slip" in text_lower:
                        print(f"Detected format: Pernod Ricard")
                        return PernodExtractor(pdf_source)
                        
                    else:
                        raise ValueError(f"Unsupported invoice format. No matching extractor found.")
                        
        except Exception as e:
            print(f"Error determining extractor: {e}")
            raise
