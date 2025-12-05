import csv
import os
from db_manager import DBManager

class ToolsManager:
    def __init__(self):
        self.db = DBManager()



    def export_library_to_csv(self, filename="library_export.csv"):
        """Exports all tracks to a CSV file."""
        self.db.cursor.execute("SELECT * FROM tracks")
        rows = self.db.cursor.fetchall()
        
        # Get column names
        col_names = [description[0] for description in self.db.cursor.description]
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(col_names)
                writer.writerows(rows)
            return True, f"Exported {len(rows)} tracks to {filename}"
        except Exception as e:
            return False, str(e)

    def close(self):
        self.db.close()
