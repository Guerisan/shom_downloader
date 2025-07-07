#!/usr/bin/env python3

import os
import sqlite3
import math
import json
from pathlib import Path

# Configuration
TILES_ROOT = "shom_tiles_complete"  # Update as needed
TILE_FORMAT = "png"
MBTILES_FILE = "shom_marine_charts.mbtiles"

def deg2tile(lat, lon, zoom):
    """Convert lat/lon to tile coordinates"""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def tile2deg(x, y, zoom):
    """Convert tile coordinates to lat/lon"""
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon

def flip_y(z, y):
    """Flip Y coordinate for TMS scheme"""
    return (2 ** z - 1) - y

def analyze_tiles(tiles_root):
    """Analyze tile structure and calculate bounds"""
    zoom_levels = {}
    
    for zoom_dir in Path(tiles_root).iterdir():
        if not zoom_dir.is_dir() or not zoom_dir.name.isdigit():
            continue
            
        z = int(zoom_dir.name)
        tiles_info = {
            'min_x': float('inf'),
            'max_x': float('-inf'),
            'min_y': float('inf'),
            'max_y': float('-inf'),
            'count': 0
        }
        
        for x_dir in zoom_dir.iterdir():
            if not x_dir.is_dir() or not x_dir.name.isdigit():
                continue
                
            x = int(x_dir.name)
            
            for tile_file in x_dir.iterdir():
                if not tile_file.name.lower().endswith(f'.{TILE_FORMAT}'):
                    continue
                    
                y_str = tile_file.stem
                if not y_str.isdigit():
                    continue
                    
                y = int(y_str)
                
                tiles_info['min_x'] = min(tiles_info['min_x'], x)
                tiles_info['max_x'] = max(tiles_info['max_x'], x)
                tiles_info['min_y'] = min(tiles_info['min_y'], y)
                tiles_info['max_y'] = max(tiles_info['max_y'], y)
                tiles_info['count'] += 1
        
        if tiles_info['count'] > 0:
            zoom_levels[z] = tiles_info
    
    return zoom_levels

def calculate_bounds(zoom_levels):
    """Calculate geographic bounds from tile data"""
    bounds = {
        'min_lat': float('inf'),
        'max_lat': float('-inf'),
        'min_lon': float('inf'),
        'max_lon': float('-inf')
    }
    
    for z, info in zoom_levels.items():
        # Calculate bounds for this zoom level
        min_lat, min_lon = tile2deg(info['min_x'], info['max_y'], z)
        max_lat, max_lon = tile2deg(info['max_x'] + 1, info['min_y'], z)
        
        bounds['min_lat'] = min(bounds['min_lat'], min_lat)
        bounds['max_lat'] = max(bounds['max_lat'], max_lat)
        bounds['min_lon'] = min(bounds['min_lon'], min_lon)
        bounds['max_lon'] = max(bounds['max_lon'], max_lon)
    
    return bounds

def create_mbtiles(tiles_root, output_file):
    """Create MBTiles file from tile directory"""
    
    print(f"Analyzing tiles in {tiles_root}...")
    zoom_levels = analyze_tiles(tiles_root)
    
    if not zoom_levels:
        print("No tiles found!")
        return False
    
    # Print analysis
    print(f"Found {len(zoom_levels)} zoom levels:")
    total_tiles = 0
    for z in sorted(zoom_levels.keys()):
        info = zoom_levels[z]
        print(f"  Zoom {z}: {info['count']} tiles "
              f"(X: {info['min_x']}-{info['max_x']}, "
              f"Y: {info['min_y']}-{info['max_y']})")
        total_tiles += info['count']
    
    bounds = calculate_bounds(zoom_levels)
    print(f"Geographic bounds: {bounds['min_lat']:.4f},{bounds['min_lon']:.4f} "
          f"to {bounds['max_lat']:.4f},{bounds['max_lon']:.4f}")
    
    # Create database
    if os.path.exists(output_file):
        os.remove(output_file)
    
    conn = sqlite3.connect(output_file)
    c = conn.cursor()
    
    # Create tables
    c.execute('''
    CREATE TABLE tiles (
        zoom_level INTEGER,
        tile_column INTEGER,
        tile_row INTEGER,
        tile_data BLOB,
        PRIMARY KEY (zoom_level, tile_column, tile_row)
    )''')
    
    c.execute('''
    CREATE TABLE metadata (
        name TEXT,
        value TEXT,
        PRIMARY KEY (name)
    )''')
    
    # Insert tiles
    inserted = 0
    
    for zoom_dir in sorted(Path(tiles_root).iterdir()):
        if not zoom_dir.is_dir() or not zoom_dir.name.isdigit():
            continue
        
        z = int(zoom_dir.name)
        print(f"Processing zoom level {z}...")
        
        for x_dir in sorted(zoom_dir.iterdir()):
            if not x_dir.is_dir() or not x_dir.name.isdigit():
                continue
            
            x = int(x_dir.name)
            
            for tile_file in sorted(x_dir.iterdir()):
                if not tile_file.name.lower().endswith(f'.{TILE_FORMAT}'):
                    continue
                
                y_str = tile_file.stem
                if not y_str.isdigit():
                    continue
                
                y = int(y_str)
                flipped_y = flip_y(z, y)
                
                try:
                    with open(tile_file, 'rb') as f:
                        tile_data = f.read()
                    
                    # Verify it's a valid image
                    if len(tile_data) < 100:  # Too small to be a valid image
                        print(f"Warning: Skipping {tile_file} - file too small")
                        continue
                    
                    c.execute('''
                    INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data)
                    VALUES (?, ?, ?, ?)
                    ''', (z, x, flipped_y, tile_data))
                    
                    inserted += 1
                    
                    if inserted % 100 == 0:
                        print(f"  Inserted {inserted}/{total_tiles} tiles...")
                        
                except Exception as e:
                    print(f"Error processing {tile_file}: {e}")
    
    # Insert metadata
    min_zoom = min(zoom_levels.keys())
    max_zoom = max(zoom_levels.keys())
    
    metadata = {
        "name": "SHOM Marine Charts",
        "format": TILE_FORMAT,
        "minzoom": str(min_zoom),
        "maxzoom": str(max_zoom),
        "bounds": f"{bounds['min_lon']},{bounds['min_lat']},{bounds['max_lon']},{bounds['max_lat']}",
        "center": f"{(bounds['min_lon'] + bounds['max_lon'])/2},{(bounds['min_lat'] + bounds['max_lat'])/2},{min_zoom + 2}",
        "version": "1.0",
        "type": "overlay",
        "attribution": "SHOM - Service Hydrographique et Océanographique de la Marine",
        "description": f"Marine charts from SHOM covering {bounds['min_lat']:.2f}°-{bounds['max_lat']:.2f}°N, {bounds['min_lon']:.2f}°-{bounds['max_lon']:.2f}°E",
        "tilestats": json.dumps({
            "layerCount": 1,
            "layers": [{
                "layer": "marine_charts",
                "count": inserted,
                "geometry": "Unknown",
                "attributeCount": 0,
                "attributes": []
            }]
        })
    }
    
    for k, v in metadata.items():
        c.execute('INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)', (k, v))
    
    # Create indexes for better performance
    c.execute('CREATE INDEX IF NOT EXISTS tile_index ON tiles (zoom_level, tile_column, tile_row)')
    
    conn.commit()
    conn.close()
    
    print(f"\nMBTiles creation complete!")
    print(f"  File: {output_file}")
    print(f"  Tiles inserted: {inserted}/{total_tiles}")
    print(f"  Zoom levels: {min_zoom}-{max_zoom}")
    print(f"  File size: {os.path.getsize(output_file) / 1024 / 1024:.1f} MB")
    
    return True

if __name__ == "__main__":
    success = create_mbtiles(TILES_ROOT, MBTILES_FILE)
    if success:
        print(f"\nReady to use with OpenCPN: {MBTILES_FILE}")
    else:
        print("Failed to create MBTiles file")
