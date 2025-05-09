import tkinter as tk
from tkinter import ttk
import json
from wellcat_parser import parse_wellcat_data

class WellCatViewer:
    def __init__(self, master, data):
        self.master = master
        self.data = data
        
        master.title("WellCat Data Viewer")
        master.geometry("800x600")
        
        # Create notebook for different data views
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Create summary tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Well Summary")
        
        # Create inventory tab  
        self.inventory_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.inventory_frame, text="Pipe Inventory")
        
        # Populate summary tab
        row = 0
        ttk.Label(self.summary_frame, text="Well Information", font=("Arial", 14, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10,20))
        
        row += 1
        for key, value in data['well_info'].items():
            ttk.Label(self.summary_frame, text=f"{key.replace('_',' ').title()}:", 
                     font=("Arial", 11, "bold")).grid(row=row, column=0, sticky="w", padx=10, pady=2)
            ttk.Label(self.summary_frame, text=str(value)).grid(row=row, column=1, sticky="w", padx=10, pady=2)
            row += 1
        
        # Populate inventory tab
        self.inventory_tree = ttk.Treeview(self.inventory_frame)
        self.inventory_tree["columns"] = tuple(data['inventory'][0].keys()) if data['inventory'] else ()
        self.inventory_tree["show"] = "headings"
        
        # Define columns
        for column in self.inventory_tree["columns"]:
            self.inventory_tree.heading(column, text=column.title())
            self.inventory_tree.column(column, width=100)
        
        # Add data rows
        for i, item in enumerate(data['inventory']):
            values = [item[col] for col in self.inventory_tree["columns"]]
            self.inventory_tree.insert("", "end", text=str(i), values=values)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.inventory_frame, orient="vertical", command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack inventory elements
        self.inventory_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Export button
        ttk.Button(master, text="Export as JSON", command=self.export_json).pack(pady=10)
    
    def export_json(self):
        with open("wellcat_data_export.json", "w") as f:
            json.dump(self.data, f, indent=2)
        tk.messagebox.showinfo("Export Complete", "Data exported to wellcat_data_export.json")

# Usage
if __name__ == "__main__":
    parsed_data = parse_wellcat_data("file.txt_streams/Contents")
    
    root = tk.Tk()
    app = WellCatViewer(root, parsed_data)
    root.mainloop()