#!/usr/bin/env python3

import math
import os
import subprocess
import sys
from pathlib import Path

# Configuration
MIN_LAT = 47.0    # Southern boundary
MAX_LAT = 50.0    # Northern boundary  
MIN_LON = -5.0    # Western boundary
MAX_LON = 2.0     # Eastern boundary

MIN_ZOOM = 8
MAX_ZOOM = 14

OUTPUT_DIR = "shom_tiles_complete"
BASE_URL = "https://services.data.shom.fr/clevisu/wmts"

def deg2tile(lat, lon, zoom):
    """Convert lat/lon to tile coordinates (Web Mercator)"""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def tile2deg(x, y, zoom):
    """Convert tile coordinates back to lat/lon (for verification)"""
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon

def download_tile(zoom, x, y, output_dir):
    """Download a single tile"""
    outdir = Path(output_dir) / str(zoom) / str(x)
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{y}.png"
    
    # Skip if already exists
    if outfile.exists() and outfile.stat().st_size > 0:
        return True, "exists"
    
    # Construct URL
    url = (f"{BASE_URL}?"
           f"layer=RASTER_MARINE_3857_WMTS&"
           f"style=normal&"
           f"tilematrixset=3857&"
           f"Service=WMTS&"
           f"Request=GetTile&"
           f"Version=1.0.0&"
           f"Format=image%2Fpng&"
           f"TileMatrix={zoom}&"
           f"TileCol={x}&"
           f"TileRow={y}")
    
    # Curl command
    cmd = [
        'curl', '-L', '--compressed', '-s',  # -s for silent
        '-H', 'Accept: image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
        '-H', 'Accept-Encoding: gzip, deflate, br, zstd',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '-H', 'Connection: keep-alive',
        '-H', 'Host: services.data.shom.fr',
        '-H', 'Origin: https://data.shom.fr',
        '-H', 'Priority: u=5, i',
        '-H', 'Referer: https://data.shom.fr/',
        '-H', 'Sec-Fetch-Dest: image',
        '-H', 'Sec-Fetch-Mode: cors',
        '-H', 'Sec-Fetch-Site: same-site',
        '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0',
        url,
        '-o', str(outfile)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Check if file exists and has content
        if outfile.exists() and outfile.stat().st_size > 1000:  # Minimum size for valid PNG
            # Verify it's actually a PNG
            with open(outfile, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'\x89PNG\r\n\x1a\n'):
                    return True, "downloaded"
        
        # If we get here, download failed
        if outfile.exists():
            outfile.unlink()  # Remove empty/invalid file
            
        return False, f"invalid_response"
        
    except subprocess.TimeoutExpired:
        if outfile.exists():
            outfile.unlink()
        return False, "timeout"
    except Exception as e:
        if outfile.exists():
            outfile.unlink()
        return False, f"error: {e}"

def main():
    print(f"Downloading SHOM tiles for area: {MIN_LAT},{MIN_LON} to {MAX_LAT},{MAX_LON}")
    print(f"Zoom levels: {MIN_ZOOM} to {MAX_ZOOM}")
    
    total_tiles = 0
    downloaded = 0
    skipped = 0
    failed = 0
    
    for zoom in range(MIN_ZOOM, MAX_ZOOM + 1):
        print(f"\nProcessing zoom level {zoom}...")
        
        # Calculate tile bounds for this zoom level
        min_x, max_y = deg2tile(MIN_LAT, MIN_LON, zoom)
        max_x, min_y = deg2tile(MAX_LAT, MAX_LON, zoom)
        
        # Ensure we have the right bounds (min_y should be less than max_y)
        if min_y > max_y:
            min_y, max_y = max_y, min_y
            
        print(f"Tile range for zoom {zoom}: X({min_x}-{max_x}) Y({min_y}-{max_y})")
        
        zoom_tiles = (max_x - min_x + 1) * (max_y - min_y + 1)
        total_tiles += zoom_tiles
        print(f"Expected tiles for this zoom level: {zoom_tiles}")
        
        zoom_downloaded = 0
        zoom_failed = 0
        
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                success, status = download_tile(zoom, x, y, OUTPUT_DIR)
                
                if success:
                    if status == "downloaded":
                        downloaded += 1
                        zoom_downloaded += 1
                    else:  # exists
                        skipped += 1
                else:
                    failed += 1
                    zoom_failed += 1
                    if zoom_failed <= 5:  # Only print first few errors per zoom level
                        print(f"  Failed to download tile {zoom}/{x}/{y}: {status}")
                
                # Progress indicator
                if (downloaded + skipped + failed) % 100 == 0:
                    print(f"  Progress: Downloaded {zoom_downloaded}, Failed {zoom_failed}")
        
        print(f"Zoom {zoom} complete: {zoom_downloaded} downloaded, {zoom_failed} failed")
    
    print(f"\nFinal results:")
    print(f"  Total expected: {total_tiles}")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped (existed): {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Success rate: {((downloaded + skipped) / total_tiles * 100):.1f}%")

if __name__ == "__main__":
    main()
