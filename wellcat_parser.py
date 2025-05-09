import struct
import re

def parse_wellcat_data(filepath):
    """Parse WellCat data into a structured format"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Create data structures to hold the parsed information
    well_info = {}
    inventory_items = []
    
    # Based on our reverse engineering, we'd implement parsing logic
    # Example structure (you'd need to adapt based on your analysis):
    
    # Parse header (assuming first 100 bytes contain header info)
    header_data = data[:100]
    
    # Find the version string (based on our earlier observation)
    version_match = re.search(b'StressData.([0-9.]+)', header_data)
    if version_match:
        well_info['version'] = version_match.group(1).decode()
    
    # Look for well name (we saw "Design #1 MANGO" in the hex dump)
    name_match = re.search(b'Design #([0-9]+) ([A-Z]+)', data)
    if name_match:
        well_info['design_number'] = int(name_match.group(1))
        well_info['well_name'] = name_match.group(2).decode()
    
    # Parse pipe inventory sections
    # (This would be based on identified record structures)
    # For example, if we found pipes stored as 32-byte records starting at offset 200:
    for i in range(200, len(data), 32):
        if i + 32 <= len(data):
            record = data[i:i+32]
            
            # Parse pipe record fields (hypothetical structure)
            try:
                diameter = struct.unpack('<f', record[0:4])[0]
                length = struct.unpack('<f', record[4:8])[0]
                grade = record[8:16].decode('ascii').strip('\x00')
                rating = struct.unpack('<f', record[16:20])[0]
                
                inventory_items.append({
                    'diameter': diameter,
                    'length': length,
                    'grade': grade,
                    'rating': rating,
                    # Add other identified fields
                })
            except:
                # Skip invalid records
                pass
    
    return {
        'well_info': well_info,
        'inventory': inventory_items
    }