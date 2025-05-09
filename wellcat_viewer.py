import tkinter as tk
from tkinter import ttk
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

class WellCatViewer:
    def __init__(self, master, data):
        self.master = master
        self.data = data
        
        master.title("WellCat Data Viewer - Wellbore Pipe Inventory")
        master.geometry("1100x700")
        
        # Create notebook for different data views
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Create tabs
        self.summary_frame = ttk.Frame(self.notebook)
        self.inventory_frame = ttk.Frame(self.notebook)
        self.grades_frame = ttk.Frame(self.notebook)
        self.pipe_detail_frame = ttk.Frame(self.notebook)
        self.graph_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.summary_frame, text="Well Summary")
        self.notebook.add(self.inventory_frame, text="Pipe Inventory")
        self.notebook.add(self.grades_frame, text="Grade Properties")
        self.notebook.add(self.pipe_detail_frame, text="Pipe Details")
        self.notebook.add(self.graph_frame, text="Visualization")
        
        # Populate tabs
        self.populate_summary()
        self.populate_inventory()
        self.populate_grades()
        self.create_visualization()
        
        # Selected pipe for details view
        self.selected_pipe = None
        
        # Export buttons
        button_frame = ttk.Frame(master)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(button_frame, text="Export as JSON", command=self.export_json).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Export as Excel", command=self.export_excel).pack(side="left", padx=5)
    
    def populate_summary(self):
        # Create header
        ttk.Label(self.summary_frame, text="Well Information", font=("Arial", 16, "bold")).pack(
            anchor="w", padx=20, pady=(20,10))
        
        # Create a frame for well info
        info_frame = ttk.Frame(self.summary_frame)
        info_frame.pack(fill="x", padx=20, pady=10)
        
        # Add well info
        row = 0
        well_info = self.data['well_info']
        
        info_items = [
            ("Version:", well_info.get('version', '')),
            ("Well Number:", well_info.get('well_number', '')),
            ("Well Name:", well_info.get('well_name', '')),
            ("Design Number:", well_info.get('design_number', '')),
            ("Design Name:", well_info.get('design_name', ''))
        ]
        
        for label, value in info_items:
            ttk.Label(info_frame, text=label, font=("Arial", 12)).grid(
                row=row, column=0, sticky="w", padx=10, pady=5)
            ttk.Label(info_frame, text=str(value), font=("Arial", 12)).grid(
                row=row, column=1, sticky="w", padx=10, pady=5)
            row += 1
        
        # Create header for inventory summary
        ttk.Label(self.summary_frame, text="Inventory Summary", font=("Arial", 16, "bold")).pack(
            anchor="w", padx=20, pady=(20,10))
        
        # Create a frame for inventory summary
        summary_frame = ttk.Frame(self.summary_frame)
        summary_frame.pack(fill="x", padx=20, pady=10)
        
        # Add pipe count
        ttk.Label(summary_frame, text="Total Pipe Count:", font=("Arial", 12)).grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        ttk.Label(summary_frame, text=str(len(self.data['pipes'])), font=("Arial", 12)).grid(
            row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Add grade distribution header
        ttk.Label(summary_frame, text="Pipe Grade Distribution:", font=("Arial", 12)).grid(
            row=1, column=0, sticky="w", padx=10, pady=(10,5))
        
        # Add grade counts
        row = 2
        grade_counts = well_info.get('grade_distribution', {})
        for grade, count in grade_counts.items():
            ttk.Label(summary_frame, text=f"{grade}:", font=("Arial", 11)).grid(
                row=row, column=0, sticky="w", padx=30, pady=2)
            ttk.Label(summary_frame, text=str(count), font=("Arial", 11)).grid(
                row=row, column=1, sticky="w", padx=10, pady=2)
            row += 1
    
    def populate_inventory(self):
        # Create tree view for pipe inventory
        columns = ("Grade", "OD (in)", "Wall (in)", "ID (in)", "Weight (ppf)", 
                  "Burst", "Collapse", "Axial")
        
        tree_frame = ttk.Frame(self.inventory_frame)
        tree_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.inventory_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        
        # Configure columns
        self.inventory_tree.heading("Grade", text="Grade")
        self.inventory_tree.heading("OD (in)", text="OD (in)")
        self.inventory_tree.heading("Wall (in)", text="Wall (in)")
        self.inventory_tree.heading("ID (in)", text="ID (in)")
        self.inventory_tree.heading("Weight (ppf)", text="Weight (ppf)")
        self.inventory_tree.heading("Burst", text="Burst Rating")
        self.inventory_tree.heading("Collapse", text="Collapse Rating")
        self.inventory_tree.heading("Axial", text="Axial Rating")
        
        for col in columns:
            self.inventory_tree.column(col, width=100, anchor="center")
        
        # Add pipe data
        for i, pipe in enumerate(self.data['pipes']):
            values = (
                pipe['grade'],
                f"{pipe.get('OD', 0):.3f}",
                f"{pipe.get('wall_thickness', 0):.3f}",
                f"{pipe.get('ID', 0):.3f}",
                f"{pipe.get('weight', 0):.1f}" if 'weight' in pipe else "",
                f"{pipe.get('burst_rating', 0):.1f}" if 'burst_rating' in pipe else "",
                f"{pipe.get('collapse_rating', 0):.1f}" if 'collapse_rating' in pipe else "",
                f"{pipe.get('axial_rating', 0):.1f}" if 'axial_rating' in pipe else ""
            )
            self.inventory_tree.insert("", "end", iid=str(i), values=values, tags=(pipe['grade'],))
        
        # Color rows by grade
        grade_colors = {
            'H-40': '#FFCCCC',  # Light red
            'J-55': '#FFEECC',  # Light orange
            'C-75': '#FFFFCC',  # Light yellow
            'L-80': '#CCFFCC',  # Light green
            'N-80': '#CCFFFF',  # Light cyan
            'C-90': '#CCCCFF',  # Light blue
            'P-105': '#EECCFF'  # Light purple
        }
        
        # Apply base colors to all rows
        for grade, color in grade_colors.items():
            self.inventory_tree.tag_configure(grade, background=color)
        
        # Handle specialized grades (L-80X9, etc)
        for pipe in self.data['pipes']:
            grade = pipe['grade']
            if grade not in grade_colors:
                base_grade = grade.split('X')[0] if 'X' in grade else grade.rstrip('k9')
                if base_grade in grade_colors:
                    self.inventory_tree.tag_configure(grade, background=grade_colors[base_grade])
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.inventory_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.inventory_tree.xview)
        self.inventory_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.inventory_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        # Bind selection event
        self.inventory_tree.bind("<<TreeviewSelect>>", self.on_pipe_select)
        
        # Filter options
        filter_frame = ttk.LabelFrame(self.inventory_frame, text="Filter Options")
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Grade:").grid(row=0, column=0, padx=5, pady=5)
        self.grade_var = tk.StringVar()
        grade_combo = ttk.Combobox(filter_frame, textvariable=self.grade_var, 
                                   values=[""] + list(self.data['grades'].keys()))
        grade_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(filter_frame, text="Apply Filter", 
                  command=self.apply_filter).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(filter_frame, text="Clear Filter", 
                  command=self.clear_filter).grid(row=0, column=3, padx=5, pady=5)
    
    def populate_grades(self):
        # Create tree view for grade properties
        columns = ("Grade", "Yield Strength (psi)", "UTS (psi)", "Young's Modulus (psi)", "Poisson's Ratio")
        
        tree_frame = ttk.Frame(self.grades_frame)
        tree_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.grade_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        
        # Configure columns
        for col in columns:
            self.grade_tree.heading(col, text=col)
            width = 150 if col != "Grade" else 100
            self.grade_tree.column(col, width=width, anchor="center")
        
        # Add grade data
        for i, (grade, props) in enumerate(self.data['grades'].items()):
            values = (
                grade,
                f"{props.get('yield_strength', 0):,}",
                f"{props.get('uts', 0):,}",
                f"{props.get('young_modulus', 0):,}",
                f"{props.get('poisson_ratio', 0):.3f}"
            )
            self.grade_tree.insert("", "end", iid=str(i), values=values, tags=(grade,))
        
        # Color rows by grade (same as inventory)
        grade_colors = {
            'H-40': '#FFCCCC',  # Light red
            'J-55': '#FFEECC',  # Light orange
            'C-75': '#FFFFCC',  # Light yellow
            'L-80': '#CCFFCC',  # Light green
            'N-80': '#CCFFFF',  # Light cyan
            'C-90': '#CCCCFF',  # Light blue
            'P-105': '#EECCFF'  # Light purple
        }
        
        for grade, color in grade_colors.items():
            self.grade_tree.tag_configure(grade, background=color)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.grade_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.grade_tree.xview)
        self.grade_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.grade_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
    
    def on_pipe_select(self, event):
        selected_items = self.inventory_tree.selection()
        if selected_items:
            index = int(selected_items[0])
            self.selected_pipe = self.data['pipes'][index]
            self.show_pipe_details()
    
    def show_pipe_details(self):
        # Clear previous content
        for widget in self.pipe_detail_frame.winfo_children():
            widget.destroy()
        
        if not self.selected_pipe:
            ttk.Label(self.pipe_detail_frame, text="Select a pipe from the inventory tab to view details").pack(
                padx=20, pady=20)
            return
        
        # Create a detailed view of the selected pipe
        pipe = self.selected_pipe
        grade_props = pipe.get('grade_properties', {})
        
        # Header
        ttk.Label(self.pipe_detail_frame, 
                 text=f"Pipe Details: {pipe['grade']} - {pipe.get('OD', 0):.3f}\"",
                 font=("Arial", 16, "bold")).pack(anchor="w", padx=20, pady=(20,10))
        
        # Create frames for different sections
        dimensions_frame = ttk.LabelFrame(self.pipe_detail_frame, text="Pipe Dimensions")
        dimensions_frame.pack(fill="x", padx=20, pady=10)
        
        ratings_frame = ttk.LabelFrame(self.pipe_detail_frame, text="Pipe Ratings")
        ratings_frame.pack(fill="x", padx=20, pady=10)
        
        grade_frame = ttk.LabelFrame(self.pipe_detail_frame, text="Grade Properties")
        grade_frame.pack(fill="x", padx=20, pady=10)
        
        # Dimensions
        dim_items = [
            ("Outer Diameter (OD):", f"{pipe.get('OD', 0):.3f} in"),
            ("Wall Thickness:", f"{pipe.get('wall_thickness', 0):.3f} in"),
            ("Inner Diameter (ID):", f"{pipe.get('ID', 0):.3f} in"),
            ("Weight:", f"{pipe.get('weight', 0):.1f} ppf" if 'weight' in pipe else "N/A")
        ]
        
        for i, (label, value) in enumerate(dim_items):
            ttk.Label(dimensions_frame, text=label, font=("Arial", 11)).grid(
                row=i//2, column=i%2*2, sticky="w", padx=10, pady=5)
            ttk.Label(dimensions_frame, text=value, font=("Arial", 11)).grid(
                row=i//2, column=i%2*2+1, sticky="w", padx=10, pady=5)
        
        # Ratings
        rating_items = [
            ("Burst Rating:", f"{pipe.get('burst_rating', 0):.1f}" if 'burst_rating' in pipe else "N/A"),
            ("Collapse Rating:", f"{pipe.get('collapse_rating', 0):.1f}" if 'collapse_rating' in pipe else "N/A"),
            ("Axial Rating:", f"{pipe.get('axial_rating', 0):.1f}" if 'axial_rating' in pipe else "N/A")
        ]
        
        for i, (label, value) in enumerate(rating_items):
            ttk.Label(ratings_frame, text=label, font=("Arial", 11)).grid(
                row=i, column=0, sticky="w", padx=10, pady=5)
            ttk.Label(ratings_frame, text=value, font=("Arial", 11)).grid(
                row=i, column=1, sticky="w", padx=10, pady=5)
        
        # Grade properties
        grade_items = [
            ("Grade:", pipe.get('grade', '')),
            ("Yield Strength:", f"{grade_props.get('yield_strength', 0):,} psi"),
            ("Ultimate Tensile Strength:", f"{grade_props.get('uts', 0):,} psi"),
            ("Young's Modulus:", f"{grade_props.get('young_modulus', 0):,} psi"),
            ("Poisson's Ratio:", f"{grade_props.get('poisson_ratio', 0):.3f}")
        ]
        
        for i, (label, value) in enumerate(grade_items):
            ttk.Label(grade_frame, text=label, font=("Arial", 11)).grid(
                row=i, column=0, sticky="w", padx=10, pady=5)
            ttk.Label(grade_frame, text=value, font=("Arial", 11)).grid(
                row=i, column=1, sticky="w", padx=10, pady=5)
    
    def create_visualization(self):
        # Clear previous content
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
        
        # Create tabs for different visualizations
        viz_notebook = ttk.Notebook(self.graph_frame)
        viz_notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        dist_frame = ttk.Frame(viz_notebook)
        od_frame = ttk.Frame(viz_notebook)
        rating_frame = ttk.Frame(viz_notebook)
        
        viz_notebook.add(dist_frame, text="Grade Distribution")
        viz_notebook.add(od_frame, text="OD Distribution")
        viz_notebook.add(rating_frame, text="Rating Comparison")
        
        # Grade distribution chart
        fig1, ax1 = plt.subplots(figsize=(8, 5))
        
        grade_counts = self.data['well_info'].get('grade_distribution', {})
        grades = list(grade_counts.keys())
        counts = [grade_counts[g] for g in grades]
        
        colors = ['#FF6666', '#FFAA66', '#FFFF66', '#66FF66', '#66FFFF', '#6666FF', '#FF66FF', 
                 '#FFBBBB', '#FFEEBB', '#EEFFBB', '#BBEEBB', '#BBCCFF', '#EECCFF']
        
        ax1.bar(grades, counts, color=colors[:len(grades)])
        ax1.set_title('Pipe Grade Distribution')
        ax1.set_xlabel('Grade')
        ax1.set_ylabel('Count')
        
        # Embed in tkinter
        canvas1 = FigureCanvasTkAgg(fig1, dist_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(expand=True, fill="both")
        
        # OD distribution chart
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        
        od_values = {}
        for pipe in self.data['pipes']:
            if 'OD' in pipe:
                od = round(pipe['OD'], 3)
                if od in od_values:
                    od_values[od] += 1
                else:
                    od_values[od] = 1
        
        ods = list(od_values.keys())
        od_counts = [od_values[od] for od in ods]
        
        ax2.bar(ods, od_counts, color='lightblue')
        ax2.set_title('Pipe OD Distribution')
        ax2.set_xlabel('OD (inches)')
        ax2.set_ylabel('Count')
        
        # Embed in tkinter
        canvas2 = FigureCanvasTkAgg(fig2, od_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(expand=True, fill="both")
        
        # Rating comparison chart
        fig3, ax3 = plt.subplots(figsize=(8, 5))
        
        # Group by grade
        grade_ratings = {}
        for pipe in self.data['pipes']:
            grade = pipe['grade']
            if grade not in grade_ratings:
                grade_ratings[grade] = {'burst': [], 'collapse': [], 'axial': []}
            
            if 'burst_rating' in pipe:
                grade_ratings[grade]['burst'].append(pipe['burst_rating'])
            if 'collapse_rating' in pipe:
                grade_ratings[grade]['collapse'].append(pipe['collapse_rating'])
            if 'axial_rating' in pipe:
                grade_ratings[grade]['axial'].append(pipe['axial_rating'])
        
        # Calculate averages
        grades = []
        burst_avgs = []
        collapse_avgs = []
        
        for grade, ratings in grade_ratings.items():
            if ratings['burst'] and ratings['collapse']:
                grades.append(grade)
                burst_avgs.append(sum(ratings['burst']) / len(ratings['burst']))
                collapse_avgs.append(sum(ratings['collapse']) / len(ratings['collapse']))
        
        # Sort by grade
        sorted_indices = sorted(range(len(grades)), key=lambda i: grades[i])
        grades = [grades[i] for i in sorted_indices]
        burst_avgs = [burst_avgs[i] for i in sorted_indices]
        collapse_avgs = [collapse_avgs[i] for i in sorted_indices]
        
        x = range(len(grades))
        width = 0.35
        
        ax3.bar([i - width/2 for i in x], burst_avgs, width, label='Burst Rating', color='green')
        ax3.bar([i + width/2 for i in x], collapse_avgs, width, label='Collapse Rating', color='blue')
        
        ax3.set_title('Average Ratings by Grade')
        ax3.set_xlabel('Grade')
        ax3.set_ylabel('Rating')
        ax3.set_xticks(x)
        ax3.set_xticklabels(grades)
        ax3.legend()
        
        # Embed in tkinter
        canvas3 = FigureCanvasTkAgg(fig3, rating_frame)
        canvas3.draw()
        canvas3.get_tk_widget().pack(expand=True, fill="both")
    
    def apply_filter(self):
        grade = self.grade_var.get()
        
        # Clear current view
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        
        # Add filtered data
        for i, pipe in enumerate(self.data['pipes']):
            if not grade or pipe['grade'] == grade:
                values = (
                    pipe['grade'],
                    f"{pipe.get('OD', 0):.3f}",
                    f"{pipe.get('wall_thickness', 0):.3f}",
                    f"{pipe.get('ID', 0):.3f}",
                    f"{pipe.get('weight', 0):.1f}" if 'weight' in pipe else "",
                    f"{pipe.get('burst_rating', 0):.1f}" if 'burst_rating' in pipe else "",
                    f"{pipe.get('collapse_rating', 0):.1f}" if 'collapse_rating' in pipe else "",
                    f"{pipe.get('axial_rating', 0):.1f}" if 'axial_rating' in pipe else ""
                )
                self.inventory_tree.insert("", "end", iid=str(i), values=values, tags=(pipe['grade'],))
    
    def clear_filter(self):
        self.grade_var.set("")
        self.apply_filter()
    
    def export_json(self):
        filename = "wellcat_data.json"
        with open(filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        tk.messagebox.showinfo("Export Complete", f"Data exported to {filename}")
    
    def export_excel(self):
        try:
            from wellcat_parser import export_to_excel
            if export_to_excel(self.data):
                tk.messagebox.showinfo("Export Complete", "Data exported to wellcat_data.xlsx")
        except ImportError:
            tk.messagebox.showerror("Export Error", "pandas module not found. Install with: pip install pandas openpyxl")

# Usage
if __name__ == "__main__":
    from wellcat_parser import parse_wellcat_data
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    contents_file = os.path.join(current_dir, "file.txt_streams", "Contents")
    
    if os.path.exists(contents_file):
        result = parse_wellcat_data(contents_file)
        
        root = tk.Tk()
        app = WellCatViewer(root, result)
        root.mainloop()
    else:
        print(f"File not found: {contents_file}")