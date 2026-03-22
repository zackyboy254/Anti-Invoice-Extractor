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
