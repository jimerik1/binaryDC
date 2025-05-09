import base64
import zlib
import olefile
import io
import sys
import os
import struct
from datetime import datetime
import binascii

def analyze_edm_file(file_path):
    print(f"Analyzing file: {file_path}")
    
    try:
        # Read the binary data from the file
        with open(file_path, 'rb') as f:
            encoded_data = f.read()
        
        print(f"Read {len(encoded_data)} bytes of encoded data")
        
        # Check if data is base64 encoded (based on first few characters)
        if encoded_data.startswith(b'eNr') or all(c in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in encoded_data[:100]):
            print("Data appears to be base64 encoded. Attempting to decode...")
            try:
                # Try to decode base64
                decoded_data = base64.b64decode(encoded_data)
                print(f"Successfully base64 decoded to {len(decoded_data)} bytes")
                
                # Save decoded data for inspection
                decoded_path = file_path + ".decoded"
                with open(decoded_path, "wb") as f:
                    f.write(decoded_data)
                print(f"Saved decoded data to {decoded_path}")
                
                # Proceed with the decoded data
                compressed_data = decoded_data
            except binascii.Error as e:
                print(f"Base64 decoding failed: {e}")
                print("Proceeding with original data...")
                compressed_data = encoded_data
        else:
            print("Data does not appear to be base64 encoded")
            compressed_data = encoded_data
        
        # Try to decompress
        try:
            decompressed_data = zlib.decompress(compressed_data)
            print(f"Successfully decompressed with standard zlib to {len(decompressed_data)} bytes")
        except zlib.error as e:
            print(f"Standard decompression failed: {e}")
            print("Trying alternative zlib parameters...")
            
            # Try with different window bits
            decompression_succeeded = False
            for wbits in [15, 31, -15]:  # Standard, gzip, raw deflate
                try:
                    decompressed_data = zlib.decompress(compressed_data, wbits=wbits)
                    print(f"Successfully decompressed with wbits={wbits} to {len(decompressed_data)} bytes")
                    decompression_succeeded = True
                    break
                except zlib.error:
                    continue
                    
            if not decompression_succeeded:
                print("All decompression attempts failed")
                return
        
        # Save decompressed data for inspection
        decompressed_path = file_path + ".decompressed"
        with open(decompressed_path, "wb") as f:
            f.write(decompressed_data)
        print(f"Saved decompressed data to {decompressed_path}")
        
        # Check for CFBF signature (D0CF11E0)
        if decompressed_data[:8] == b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1':
            print("Decompressed data has Microsoft Compound File Binary Format signature")
        else:
            print("Warning: Decompressed data does not have CFBF signature")
        
        # Create a file-like object from the decompressed data
        ole_stream = io.BytesIO(decompressed_data)
        
        # Try to open as an OLE file (using correct class name OleFileIO)
        try:
            ole = olefile.OleFileIO(ole_stream)
            print("\n===== CFBF File Analysis =====")
            
            # Get and print metadata (updated approach)
            try:
                if ole.exists('\x05DocumentSummaryInformation'):
                    print("\nDocument Summary Information exists")
                
                if ole.exists('\x05SummaryInformation'):
                    print("\nSummary Information exists")
                    summary = ole.getproperties('\x05SummaryInformation')
                    print("\nMetadata:")
                    # Map property IDs to names
                    prop_names = {
                        2: "Title",
                        3: "Subject",
                        4: "Author",
                        5: "Keywords",
                        6: "Comments",
                        8: "Last saved by",
                        9: "Revision number",
                        12: "Creation date",
                        13: "Last saved time",
                        14: "Number of pages",
                        18: "Application name",
                        19: "Security"
                    }
                    for prop_id, value in summary.items():
                        name = prop_names.get(prop_id, f"Property ID {prop_id}")
                        # Format dates if needed
                        if isinstance(value, datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        print(f"  {name}: {value}")
            except Exception as e:
                print(f"Error extracting metadata: {e}")
            
            # List all streams (files) in the OLE file
            print("\nFile Structure:")
            for i, stream_path in enumerate(ole.listdir()):
                # Convert the tuple path to a string
                if isinstance(stream_path, list) or isinstance(stream_path, tuple):
                    path_str = "/".join(stream_path)
                else:
                    path_str = stream_path
                
                # Get stream size
                try:
                    stream_size = ole.get_size(stream_path)
                    print(f"\n[Stream {i+1}] {path_str}")
                    print(f"  Size: {stream_size} bytes")
                    
                    # Read the stream data (with a reasonable size limit)
                    max_read = min(stream_size, 10000)  # Limit to 10KB for large streams
                    stream_data = ole.openstream(stream_path).read(max_read)
                    
                    # Display a hex dump of the first 100 bytes
                    print(f"  Hex dump (first 100 bytes):")
                    for j in range(0, min(len(stream_data), 100), 16):
                        hex_values = ' '.join(f"{stream_data[j+k]:02x}" for k in range(min(16, len(stream_data)-j)))
                        ascii_values = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in stream_data[j:j+16])
                        print(f"    {j:04x}: {hex_values:<47} | {ascii_values}")
                    
                    # Try to detect if it's text content
                    if all(b == 0 or 32 <= b <= 126 or b in (9, 10, 13) for b in stream_data[:100]):
                        try:
                            # Handle potential UTF-16 encoding (common in Microsoft files)
                            if len(stream_data) >= 2 and stream_data[0] == 0xFF and stream_data[1] == 0xFE:
                                text_sample = stream_data[:200].decode('utf-16-le')
                            else:
                                text_sample = stream_data[:200].decode('utf-8', errors='replace')
                            
                            print(f"  Text sample:")
                            print(f"    {text_sample.replace(chr(0), '').strip()}")
                        except Exception:
                            pass
                    
                    # Export stream to a file for further analysis
                    export_dir = file_path + "_streams"
                    if not os.path.exists(export_dir):
                        os.makedirs(export_dir)
                    
                    # Create a safe filename
                    if isinstance(stream_path, list) or isinstance(stream_path, tuple):
                        safe_name = '_'.join(stream_path).replace('\\', '_').replace('/', '_')
                    else:
                        safe_name = stream_path.replace('\\', '_').replace('/', '_')
                    
                    # Ensure filename is valid
                    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-.')
                    if not safe_name:
                        safe_name = f"stream_{i+1}"
                    
                    export_path = os.path.join(export_dir, safe_name)
                    
                    with open(export_path, 'wb') as f:
                        f.write(stream_data)
                    print(f"  Saved to: {export_path}")
                    
                except Exception as e:
                    print(f"  Error processing stream {path_str}: {e}")
            
            ole.close()
            print(f"\nComplete analysis saved to directory: {export_dir}")
            
        except Exception as e:
            print(f"\nError opening as CFBF: {e}")
            print("This does not appear to be a valid CFBF file after decompression.")
            print("Analyzing decompressed data as raw binary...")
            
            # Basic analysis of the binary data
            print("\nDecompressed Data Analysis:")
            print(f"  Size: {len(decompressed_data)} bytes")
            
            # Check for common file signatures
            signatures = {
                b'PK\x03\x04': 'ZIP archive',
                b'\x50\x4B\x03\x04': 'ZIP archive',
                b'\x1F\x8B\x08': 'GZIP archive',
                b'\x42\x5A\x68': 'BZIP2 archive',
                b'\x37\x7A\xBC\xAF\x27\x1C': '7Z archive',
                b'\x52\x61\x72\x21\x1A\x07': 'RAR archive',
                b'\x7F\x45\x4C\x46': 'ELF executable',
                b'\x4D\x5A': 'Windows executable (MZ)',
                b'\xFF\xD8\xFF': 'JPEG image',
                b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': 'PNG image',
                b'\x25\x50\x44\x46': 'PDF document',
                b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': 'MS Office document (OLE)',
                b'\x50\x4B\x03\x04\x14\x00\x06\x00': 'MS Office document (OOXML)',
                b'\x3C\x3F\x78\x6D\x6C': 'XML document',
                b'\x7B': 'JSON document (starts with {)',
                b'\x1F\x8B': 'GZIP file'
            }
            
            for sig, file_type in signatures.items():
                if decompressed_data.startswith(sig):
                    print(f"  Detected file type: {file_type}")
                    break
            else:
                print("  No common file signature detected")
            
            # Show hex dump of first part of file
            print("\nHex dump (first 256 bytes):")
            for i in range(0, min(len(decompressed_data), 256), 16):
                hex_values = ' '.join(f"{decompressed_data[i+j]:02x}" for j in range(min(16, len(decompressed_data)-i)))
                ascii_values = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in decompressed_data[i:i+16])
                print(f"  {i:04x}: {hex_values:<47} | {ascii_values}")
            
            # Try to interpret as text if it seems like it might be
            if all(b == 0 or 32 <= b <= 126 or b in (9, 10, 13) for b in decompressed_data[:100]):
                try:
                    text_sample = decompressed_data[:500].decode('utf-8', errors='replace')
                    print("\nSample as text (first 500 chars):")
                    print(text_sample)
                except Exception:
                    pass
    
    except Exception as e:
        print(f"Error analyzing file: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "file.txt"  # Default filename
    
    analyze_edm_file(file_path)