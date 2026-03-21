from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """
    Abstract base class for all invoice extractors.
    Any new vendor format simply needs to implement this class.
    """
    def __init__(self, pdf_source):
        self.pdf_source = pdf_source
        
        # This acts as the standard state of the parser before saving to excel.
        # This will hold common fields like 'CustomerName', 'OrderNumber' mapped 
        # appropriately per line.
        self.extracted_items = []
        
    @abstractmethod
    def extract(self) -> list[dict]:
        """
        Extracts data from the PDF and returns a list of dictionaries,
        where each dictionary represents a single item row matching the standard columns.
        
        Returns:
            list[dict]: A list of rows ready to be appended to the Excel output.
        """
        return []
        
    def _create_standard_row(self, 
                             company_name=None,
                             ship_to_name=None,
                             order_number=None,
                             customer_name=None,
                             product_code=None,
                             product_description=None,
                             cases=None,
                             units=None,
                             uom=None,
                             qty_ordered=None,
                             weight=None) -> dict:
        """
        Helper function to ensure extracted data maps perfectly to the Excel layout.
        """
        return {
            "CompanyName": company_name,
            "ShipToName": ship_to_name,
            "OrderNumber": order_number,
            "CustomerName": customer_name,
            "ProductCode": product_code,
            "ProductDescription": product_description,
            "Cases": cases,
            "Units": units,
            "UOM": uom,
            "QtyOrdered": qty_ordered,
            "Weight": weight
        }
