import pandas as pd
import io

class WebExcelWriter:
    """
    Handles in-memory Excel generation with support for adding and removing
    data associated with specific file IDs.
    """
    def __init__(self):
        # Standard columns that every extracted invoice should have
        self.columns = [
            "CompanyName", "ShipToName", "OrderNumber", "CustomerName",
            "ProductCode", "ProductDescription", "Cases", "Units",
            "UOM", "QtyOrdered", "Weight"
        ]
        
        # Internal storage: List of dicts with metadata
        # Each entry: {"file_id": str, "sheet": str, "rows": list[dict]}
        self.records = []
            
    def append_data(self, data: list[dict], file_id: str, sheet_name: str = "Sheet1"):
        """
        Appends a list of row dictionaries associated with a file_id.
        """
        if not data:
            return
            
        self.records.append({
            "file_id": file_id,
            "sheet": sheet_name,
            "rows": data
        })
        
    def remove_file_data(self, file_id: str):
        """
        Removes all data entries associated with the given file_id.
        """
        self.records = [r for r in self.records if r["file_id"] != file_id]

    def get_excel_bytes(self) -> io.BytesIO:
        """
        Groups all current records by sheet name and returns an Excel BytesIO stream.
        """
        output = io.BytesIO()
        
        # Group rows by sheet
        sheet_groups: dict[str, list[dict]] = {}
        for rec in self.records:
            s_name = str(rec.get("sheet", "Sheet1"))
            # Clean up sheet name (Excel limits to 31 chars and no special chars)
            safe_name = "".join([c for c in s_name if c.isalnum() or c in (' ', '_')]).strip()[:31] # type: ignore
            if not safe_name: safe_name = "Sheet1"
            
            if safe_name not in sheet_groups:
                sheet_groups[safe_name] = []
            
            rows = rec.get("rows", [])
            sheet_groups[safe_name].extend(list(rows)) # type: ignore
            
        # If no data, provide an empty template
        if not sheet_groups:
            sheet_groups["Sheet1"] = []

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for s_name, rows in sheet_groups.items():
                df = pd.DataFrame(rows)
                # Ensure all standard columns exist and are ordered
                for col in self.columns:
                    if col not in df.columns:
                        df[col] = None
                df = df[self.columns]
                df.to_excel(writer, index=False, sheet_name=s_name)
                
        output.seek(0)
        return output
