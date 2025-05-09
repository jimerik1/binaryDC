import struct
import re
import json
import os
import numpy as np

def parse_wellcat_data(filepath):
    """Parse WellCat data into a structured format for oil/gas pipe inventory"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Create main data structures
    well_info = {}
    pipe_inventory = []
    grades = {}
    packers = find_packer_information(data)

    
    # Parse basic well info 
    version_match = re.search(b'StressData.([0-9.]+)', data[:100])
    if version_match:
        well_info['version'] = version_match.group(1).decode()
    
    well_name_match = re.search(b'Wellbore #([0-9]+) ([A-Z]+)', data)
    if well_name_match:
        well_info['well_number'] = int(well_name_match.group(1))
        well_info['well_name'] = well_name_match.group(2).decode()
    
    design_match = re.search(b'Design #([0-9]+) ([A-Z]+)', data)
    if design_match:
        well_info['design_number'] = int(design_match.group(1))
        well_info['design_name'] = design_match.group(2).decode()
    
    # Extract grade specs
    # These are the standard API grades
    grade_patterns = [b'H-40', b'J-55', b'C-75', b'L-80', b'N-80', b'C-90', b'P-105', 
                      b'L-80', b'C-90', b'H-40', b'J-55', b'C-75', b'N-80', 
                      b'L-80', b'C-90', b'L-80', b'C-90', b'P-105', b'H-40', b'J-55',]
    
    # First, define grade properties
    for grade_name in grade_patterns:
        grade_str = grade_name.decode()
        
        # Extract yield and UTS values based on API specifications
        # These are standard values for API grades
        if grade_str == 'H-40':
            yield_strength = 40000  # psi
            uts = 60000  # psi
        elif grade_str == 'J-55':
            yield_strength = 55000
            uts = 75000
        elif grade_str == 'C-75':
            yield_strength = 75000
            uts = 95000
        elif grade_str == 'L-80':
            yield_strength = 80000
            uts = 95000
        elif grade_str == 'N-80':
            yield_strength = 80000
            uts = 100000
        elif grade_str == 'C-90':
            yield_strength = 90000
            uts = 105000
        elif grade_str == 'P-105':
            yield_strength = 105000
            uts = 120000
        else:
            # For special grades, estimate based on the base grade
            base_grade = grade_str.split('X')[0] if 'X' in grade_str else grade_str.rstrip('k9')
            if base_grade == 'L-80':
                yield_strength = 80000
                uts = 95000
            elif base_grade == 'C-90':
                yield_strength = 90000
                uts = 105000
            else:
                yield_strength = 55000  # Default
                uts = 75000
        
        grades[grade_str] = {
            'yield_strength': yield_strength,
            'uts': uts,
            'young_modulus': 30000000,  # psi, standard for steel
            'poisson_ratio': 0.3        # standard for steel
        }
    
    # Now identify pipe records
    # Look for patterns where a grade is followed by measurements
    for grade_name in grade_patterns:
        grade_str = grade_name.decode()
        
        # Find all occurrences of this grade in the file
        for match in re.finditer(grade_name, data):
            offset = match.start()
            
            # Get the next 100 bytes to analyze for pipe record data
            record_data = data[offset:offset+200]
            
            # Extract pipe specifications
            pipe_record = {
                'grade': grade_str,
                'offset': offset,
            }
            
            # Look for float values that would represent OD, wall thickness, etc.
            float_values = []
            for i in range(0, len(record_data)-8, 4):
                try:
                    float_val = struct.unpack('<f', record_data[i:i+4])[0]
                    if 0.01 < float_val < 100000:  # Reasonable range for pipe specs
                        float_values.append((i, float_val))
                except:
                    pass
            
            # Also look for doubles
            double_values = []
            for i in range(0, len(record_data)-8, 8):
                try:
                    double_val = struct.unpack('<d', record_data[i:i+8])[0]
                    if 0.01 < double_val < 100000:  # Reasonable range
                        double_values.append((i, double_val))
                except:
                    pass
            
            # Based on the observed patterns in the hex dump and analysis report
            # OD and wall thickness appear to be in float values
            if len(float_values) >= 2:
                # Likely format based on the file analysis:
                # First value is usually OD
                # Second value is usually wall thickness or ID
                od_val = None
                wall_thickness = None
                
                # Look for values in the right range for OD (inches)
                for _, val in float_values:
                    if 0.5 < val < 30.0:  # Typical range for pipe OD in inches
                        if od_val is None:
                            od_val = val
                        elif wall_thickness is None:
                            wall_thickness = val
                            break
                
                if od_val:
                    pipe_record['OD'] = od_val
                
                if wall_thickness:
                    pipe_record['wall_thickness'] = wall_thickness
                    # Calculate ID from OD and wall thickness
                    if od_val:
                        pipe_record['ID'] = od_val - 2 * wall_thickness
            
            # Rating values are often found in double-precision values
            # Typically found in the pattern seen in the hex dump
            rating_values = [val for _, val in double_values if 50 < val < 500]
            
            if rating_values:
                if len(rating_values) >= 1:
                    pipe_record['burst_rating'] = rating_values[0]
                if len(rating_values) >= 2:
                    pipe_record['collapse_rating'] = rating_values[1]
                if len(rating_values) >= 3:
                    pipe_record['axial_rating'] = rating_values[2]
            
            # Weight is typically in a specific range for pipe weight (ppf)
            weight_vals = [val for _, val in float_values if 30 < val < 200]
            if weight_vals:
                pipe_record['weight'] = weight_vals[0]
            
            # Only add if we have at least OD and grade
            if 'OD' in pipe_record:
                pipe_inventory.append(pipe_record)
    
    # Filter out duplicate records (same grade, OD, and wall thickness)
    unique_pipes = []
    seen_specs = set()
    
    for pipe in pipe_inventory:
        # Create a key from critical specifications
        if 'OD' in pipe and 'wall_thickness' in pipe:
            spec_key = (pipe['grade'], round(pipe['OD'], 3), round(pipe['wall_thickness'], 3))
            
            if spec_key not in seen_specs:
                seen_specs.add(spec_key)
                unique_pipes.append(pipe)
    
    # Add grade properties to each pipe record
    for pipe in unique_pipes:
        if pipe['grade'] in grades:
            pipe['grade_properties'] = grades[pipe['grade']]
    
    # Sort by grade and OD
    unique_pipes.sort(key=lambda x: (x['grade'], x.get('OD', 0)))
    
    # Count pipes by grade for inventory summary
    grade_counts = {}
    for pipe in unique_pipes:
        grade = pipe['grade']
        if grade in grade_counts:
            grade_counts[grade] += 1
        else:
            grade_counts[grade] = 1
    
    well_info['pipe_count'] = len(unique_pipes)
    well_info['grade_distribution'] = grade_counts
    
    return {
        'well_info': well_info,
        'pipes': unique_pipes,
        'grades': grades,
        'packers': packers  # Add the packers list
    }

def export_to_excel(data, output_file="wellcat_data.xlsx"):
    """Export parsed data to Excel format"""
    try:
        import pandas as pd
        
        # Create pipe data DataFrame
        pipe_data = []
        for pipe in data['pipes']:
            pipe_row = {
                'Grade': pipe['grade'],
                'OD (in)': pipe.get('OD'),
                'Wall Thickness (in)': pipe.get('wall_thickness'),
                'ID (in)': pipe.get('ID'),
                'Weight (ppf)': pipe.get('weight'),
                'Burst Rating': pipe.get('burst_rating'),
                'Collapse Rating': pipe.get('collapse_rating'),
                'Axial Rating': pipe.get('axial_rating')
            }
            
            # Add grade properties
            if 'grade_properties' in pipe:
                pipe_row['Yield Strength (psi)'] = pipe['grade_properties'].get('yield_strength')
                pipe_row['UTS (psi)'] = pipe['grade_properties'].get('uts')
                pipe_row['Young\'s Modulus (psi)'] = pipe['grade_properties'].get('young_modulus')
                pipe_row['Poisson\'s Ratio'] = pipe['grade_properties'].get('poisson_ratio')
            
            pipe_data.append(pipe_row)
        
        # Create pipe DataFrame
        pipe_df = pd.DataFrame(pipe_data)
        
        # Create grade DataFrame
        grade_data = []
        for grade_name, props in data['grades'].items():
            grade_row = {
                'Grade': grade_name,
                'Yield Strength (psi)': props.get('yield_strength'),
                'UTS (psi)': props.get('uts'),
                'Young\'s Modulus (psi)': props.get('young_modulus'),
                'Poisson\'s Ratio': props.get('poisson_ratio')
            }
            grade_data.append(grade_row)
        
        grade_df = pd.DataFrame(grade_data)
        
        # Create well info DataFrame
        well_info = data['well_info']
        well_data = {
            'Property': ['Version', 'Well Number', 'Well Name', 'Design Number', 'Design Name', 'Pipe Count'],
            'Value': [
                well_info.get('version', ''),
                well_info.get('well_number', ''),
                well_info.get('well_name', ''),
                well_info.get('design_number', ''),
                well_info.get('design_name', ''),
                well_info.get('pipe_count', 0)
            ]
        }
        well_df = pd.DataFrame(well_data)
        
        # Grade distribution
        if 'grade_distribution' in well_info:
            dist_data = {
                'Grade': list(well_info['grade_distribution'].keys()),
                'Count': list(well_info['grade_distribution'].values())
            }
            dist_df = pd.DataFrame(dist_data)
        else:
            dist_df = pd.DataFrame({'Grade': [], 'Count': []})
        
        # Add packer data if available
        if 'packers' in data and data['packers']:
            packer_data = []
            for packer in data['packers']:
                packer_row = {
                    'Type': packer.get('type', ''),
                    'Depth (ft)': packer.get('depth', ''),
                    'Plug Depth (ft)': packer.get('plug_depth', '')
                }
                packer_data.append(packer_row)
            
            packer_df = pd.DataFrame(packer_data)
        else:
            packer_df = pd.DataFrame({'Type': [], 'Depth (ft)': [], 'Plug Depth (ft)': []})
        
        # Write to Excel file
        with pd.ExcelWriter(output_file) as writer:
            well_df.to_excel(writer, sheet_name='Well Info', index=False)
            pipe_df.to_excel(writer, sheet_name='Pipe Inventory', index=False)
            grade_df.to_excel(writer, sheet_name='Grade Properties', index=False)
            dist_df.to_excel(writer, sheet_name='Grade Distribution', index=False)
            packer_df.to_excel(writer, sheet_name='Packers', index=False)
        
        print(f"Data exported to {output_file}")
        return True
    except ImportError:
        print("pandas module not found. Install with: pip install pandas openpyxl")
        return False
    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        return False

def find_packer_information(data_bytes):
    """Attempt to find packer-related information in the binary data"""
    packers = []
    
    # Look for packer-related text
    packer_keywords = [b'packer', b'Packer', b'PACKER', b'plug', b'Plug', b'PLUG', b'seal', b'Seal', b'SEAL']
    
    for keyword in packer_keywords:
        for match in re.finditer(keyword, data_bytes):
            offset = match.start()
            packer_type = keyword.decode()
            
            # Extract surrounding 200 bytes to analyze
            context = data_bytes[max(0, offset-100):min(len(data_bytes), offset+100)]
            
            # Look for potential depth values (common range for depths in feet: 100-30000)
            depth_values = []
            for i in range(0, len(context)-4, 4):
                try:
                    val = struct.unpack('<f', context[i:i+4])[0]
                    # Filter for reasonable depth values
                    if 100 < val < 30000:
                        depth_values.append((i, val))
                except:
                    pass
            
            # Look for double-precision depth values
            for i in range(0, len(context)-8, 8):
                try:
                    val = struct.unpack('<d', context[i:i+8])[0]
                    # Filter for reasonable depth values
                    if 100 < val < 30000:
                        depth_values.append((i, val))
                except:
                    pass
            
            # If we found depth values, add a packer record
            if depth_values:
                # Get the first depth value as the most likely packer depth
                depth = depth_values[0][1]
                
                # Check if we already have this packer (avoid duplicates)
                duplicate = False
                for existing in packers:
                    if abs(existing.get('depth', 0) - depth) < 10:  # Within 10 feet
                        duplicate = True
                        break
                
                if not duplicate:
                    packer_record = {
                        'type': packer_type,
                        'depth': depth,
                        'offset': offset
                    }
                    
                    # If we have more depth values, second might be plug depth
                    if len(depth_values) > 1:
                        packer_record['plug_depth'] = depth_values[1][1]
                    
                    packers.append(packer_record)
    
    # Sort packers by depth
    packers.sort(key=lambda p: p.get('depth', 0))
    
    return packers


if __name__ == "__main__":
    import os
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    contents_file = os.path.join(current_dir, "file.txt_streams", "Contents")
    
    if os.path.exists(contents_file):
        print(f"Analyzing file: {contents_file}")
        result = parse_wellcat_data(contents_file)
        
        # Print basic summary
        well_info = result['well_info']
        print("\nWELL INFORMATION:")
        print(f"Version: {well_info.get('version', 'Unknown')}")
        print(f"Well: #{well_info.get('well_number', '')} {well_info.get('well_name', '')}")
        print(f"Design: #{well_info.get('design_number', '')} {well_info.get('design_name', '')}")
        
        # Print pipe count
        print(f"\nTotal Pipes: {len(result['pipes'])}")
        
        # Print grade distribution
        if 'grade_distribution' in well_info:
            print("\nGRADE DISTRIBUTION:")
            for grade, count in well_info['grade_distribution'].items():
                print(f"  {grade}: {count}")
        
        # Export to JSON
        with open('wellcat_data.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\nData exported to wellcat_data.json")
        
        # Try to export to Excel
        export_to_excel(result)
    else:
        print(f"File not found: {contents_file}")