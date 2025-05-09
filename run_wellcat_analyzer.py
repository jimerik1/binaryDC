import os
import sys
import tkinter as tk
from wellcat_parser import parse_wellcat_data
from wellcat_viewer import WellCatViewer

def main():
    # Get path to Contents file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    contents_file = os.path.join(current_dir, "file.txt_streams", "Contents")
    
    if not os.path.exists(contents_file):
        print(f"Error: Could not find file {contents_file}")
        print(f"Current directory: {current_dir}")
        sys.exit(1)
    
    # Parse the data
    print(f"Parsing WellCat data from {contents_file}...")
    try:
        parsed_data = parse_wellcat_data(contents_file)
        print(f"Successfully parsed data with {len(parsed_data.get('pipe_inventory', []))} pipe records")
    except Exception as e:
        print(f"Error parsing data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Launch the viewer
    print("Launching WellCat Viewer...")
    root = tk.Tk()
    app = WellCatViewer(root, parsed_data)
    root.mainloop()

if __name__ == "__main__":
    main()