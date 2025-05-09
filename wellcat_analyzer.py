import struct
import os
import collections
import matplotlib.pyplot as plt
import numpy as np

def reverse_engineer_wellcat_format(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Create a detailed report file
    with open('wellcat_analysis_report.txt', 'w') as report:
        report.write(f"WellCat Data Analysis\n")
        report.write(f"==================\n\n")
        report.write(f"File size: {len(data)} bytes\n\n")
        
        # 1. Find all text strings
        report.write("TEXT STRINGS:\n")
        strings = []
        offset = 0
        while offset < len(data):
            # Look for string markers (common patterns like length+string)
            if data[offset:offset+1].isalpha():
                # Try to extract a string
                end = offset
                while end < len(data) and (32 <= data[end] <= 126 or data[end] in (0, 9, 10, 13)):
                    end += 1
                
                if end - offset >= 3:  # Only record strings of reasonable length
                    string_data = data[offset:end].decode('ascii', errors='replace')
                    strings.append((offset, string_data))
                    report.write(f"Offset {offset}: {string_data}\n")
                
                offset = end
            else:
                offset += 1
        
        # 2. Find potential numeric fields
        report.write("\nNUMERIC VALUES:\n")
        
        # Look for 4-byte float values
        for i in range(0, len(data)-4, 4):
            try:
                value = struct.unpack('<f', data[i:i+4])[0]
                # Keep only reasonable values for well data
                if 0.001 < abs(value) < 100000 and not float('nan') == value:
                    report.write(f"Offset {i} - Float32: {value}\n")
            except:
                pass
        
        # Look for 8-byte double values
        for i in range(0, len(data)-8, 8):
            try:
                value = struct.unpack('<d', data[i:i+8])[0]
                # Keep only reasonable values for well data
                if 0.001 < abs(value) < 100000 and not float('nan') == value:
                    report.write(f"Offset {i} - Double64: {value}\n")
            except:
                pass
        
        # 3. Look for repeating patterns that might indicate records
        pattern_size = 16  # Try various sizes
        report.write(f"\nREPEATING PATTERNS (size {pattern_size}):\n")
        patterns = collections.Counter()
        
        for i in range(0, len(data) - pattern_size, pattern_size):
            pattern = data[i:i+pattern_size]
            patterns[pattern] += 1
        
        # Report the most common patterns
        for pattern, count in patterns.most_common(20):
            if count > 2:  # Only patterns that repeat
                hex_pattern = ' '.join(f'{b:02x}' for b in pattern)
                report.write(f"Pattern repeated {count} times: {hex_pattern}\n")
        
        # 4. Visualize data patterns to spot structures
        # Make a grayscale image of the data bytes to visualize patterns
        width = 512
        height = len(data) // width + 1
        img_data = np.zeros((height, width), dtype=np.uint8)
        
        for i in range(len(data)):
            row = i // width
            col = i % width
            if row < height and col < width:
                img_data[row, col] = data[i]
        
        plt.figure(figsize=(12, 8))
        plt.imshow(img_data, cmap='gray')
        plt.title('Binary Data Visualization')
        plt.savefig('data_visualization.png')
    
    print(f"Analysis complete. See wellcat_analysis_report.txt for details")
    
    # Return found string list for further analysis
    return strings