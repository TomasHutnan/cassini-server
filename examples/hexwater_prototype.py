import requests
import rasterio
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import math
import h3
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import json
import time
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# ==================== CONFIGURATION ====================
# Location (latitude, longitude)
CENTER_LAT, CENTER_LON = 48.69740220446884, 21.28180222871356

# Area size in meters (width, height)
AREA_SIZE_M = (1000, 1000)  # 1km x 1km

# Hexagon resolution in meters (approximate diameter of each hex)
HEX_SIZE_M = 10  # 10 meters per hex

# ==================================================

# Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Biome definitions
BIOMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Herbaceous wetland",
    60: "Mangroves",
    70: "Moss and lichen",
    80: "Bare/sparse vegetation",
    90: "Built-up",
    100: "Permanent water bodies",
    110: "Snow and ice",
    254: "Unclassifiable",
}

BIOME_COLORS = {
    "Tree cover": "#006400",
    "Shrubland": "#ffbb22",
    "Grassland": "#ffff4c",
    "Cropland": "#f096ff",
    "Herbaceous wetland": "#0096a0",
    "Mangroves": "#00cf75",
    "Moss and lichen": "#fae6a0",
    "Bare/sparse vegetation": "#b4b4b4",
    "Permanent water bodies": "#0064c8",
    "Snow and ice": "#f0f0f0",
    "Unclassifiable": "#0a0a0a",
}


def get_euhydro_rivers(lat_min, lat_max, lon_min, lon_max, layer_ids=None):
    """Fetch river line features from EU-Hydro ArcGIS service as LineStrings.

    Parallelizes requests per sublayer for speed. Pagination within a layer
    remains sequential.
    """
    base_url = (
        "https://image.discomap.eea.europa.eu/arcgis/rest/services/"
        "EUHydro/EUHydro_RiverNetworkDatabase/MapServer"
    )

    if layer_ids is None:
        layer_ids = list(range(7, 14))  # Strahler 3..9 (exclude 1 & 2)

    # Envelope in EPSG:4326
    envelope = {
        "xmin": float(lon_min),
        "ymin": float(lat_min),
        "xmax": float(lon_max),
        "ymax": float(lat_max),
        "spatialReference": {"wkid": 4326},
    }

    page_size = 1000

    def fetch_layer(layer_id):
        query_url = f"{base_url}/{layer_id}/query"
        layer_rivers = []
        result_offset = 0
        while True:
            params = {
                "f": "geojson",
                "where": "1=1",
                "geometry": json.dumps(envelope),
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": 4326,
                "resultRecordCount": page_size,
                "resultOffset": result_offset,
            }
            try:
                resp = requests.get(query_url, params=params, timeout=60)
            except Exception as e:
                print(f"EU-Hydro request error on layer {layer_id}: {e}")
                break
            if resp.status_code != 200:
                print(
                    f"EU-Hydro query error {resp.status_code} on layer {layer_id}"
                )
                break
            data = resp.json()
            features = data.get("features", [])
            if not features:
                break
            for feat in features:
                geom = feat.get("geometry") or {}
                gtype = geom.get("type")
                if gtype == "LineString":
                    coords = geom.get("coordinates", [])
                    if len(coords) >= 2:
                        layer_rivers.append(
                            {"type": "LineString", "coordinates": coords}
                        )
                elif gtype == "MultiLineString":
                    for part in geom.get("coordinates", []):
                        if len(part) >= 2:
                            layer_rivers.append(
                                {"type": "LineString", "coordinates": part}
                            )
            if len(features) < page_size:
                break
            result_offset += page_size
        return layer_rivers

    from concurrent.futures import ThreadPoolExecutor, as_completed

    rivers = []
    max_workers = min(8, len(layer_ids)) if layer_ids else 4
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_layer, lid): lid for lid in layer_ids}
        for future in as_completed(futures):
            try:
                rivers.extend(future.result())
            except Exception as e:
                lid = futures[future]
                print(f"EU-Hydro layer {lid} failed: {e}")

    print(f"Fetched {len(rivers)} rivers from EU-Hydro (layers {layer_ids})")
    return rivers


def get_euhydro_lakes(lat_min, lat_max, lon_min, lon_max, layer_ids=None):
    """Fetch lake/waterbody polygons from EU-Hydro as Polygon rings.

    Parallelizes requests per sublayer. Returns a flat list of Polygons.
    """
    base_url = (
        "https://image.discomap.eea.europa.eu/arcgis/rest/services/"
        "EUHydro/EUHydro_RiverNetworkDatabase/MapServer"
    )
    if layer_ids is None:
        layer_ids = [19, 2, 3]

    envelope = {
        "xmin": float(lon_min),
        "ymin": float(lat_min),
        "xmax": float(lon_max),
        "ymax": float(lat_max),
        "spatialReference": {"wkid": 4326},
    }

    page_size = 500

    def fetch_layer(layer_id):
        query_url = f"{base_url}/{layer_id}/query"
        layer_lakes = []
        result_offset = 0
        while True:
            params = {
                "f": "geojson",
                "where": "1=1",
                "geometry": json.dumps(envelope),
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": 4326,
                "resultRecordCount": page_size,
                "resultOffset": result_offset,
            }
            try:
                resp = requests.get(query_url, params=params, timeout=60)
            except Exception as e:
                print(f"EU-Hydro lakes request error on layer {layer_id}: {e}")
                break
            if resp.status_code != 200:
                print(
                    f"EU-Hydro lakes query error {resp.status_code} on layer {layer_id}"
                )
                break
            data = resp.json()
            features = data.get("features", [])
            if not features:
                break
            for feat in features:
                geom = feat.get("geometry") or {}
                gtype = geom.get("type")
                if gtype == "Polygon":
                    rings = geom.get("coordinates", [])
                    if rings:
                        layer_lakes.append(
                            {"type": "Polygon", "coordinates": rings}
                        )
                elif gtype == "MultiPolygon":
                    for poly in geom.get("coordinates", []):
                        if poly:
                            layer_lakes.append(
                                {"type": "Polygon", "coordinates": poly}
                            )
            if len(features) < page_size:
                break
            result_offset += page_size
        return layer_lakes

    from concurrent.futures import ThreadPoolExecutor, as_completed

    lakes = []
    max_workers = min(6, len(layer_ids)) if layer_ids else 3
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_layer, lid): lid for lid in layer_ids}
        for future in as_completed(futures):
            try:
                lakes.extend(future.result())
            except Exception as e:
                lid = futures[future]
                print(f"EU-Hydro lakes layer {lid} failed: {e}")

    print(f"Fetched {len(lakes)} lakes from EU-Hydro (layers {layer_ids})")
    return lakes


def fill_buildup_and_water(grid):
    """Replace built-up and water cells with neighboring biomes."""
    height, width = len(grid), len(grid[0])
    result = [row[:] for row in grid]
    to_fill = {
        (i, j)
        for i in range(height)
        for j in range(width)
        if result[i][j] in ["Built-up", "Permanent water bodies"]
    }

    while to_fill:
        filled = []
        for i, j in to_fill:
            neighbors = [
                result[ni][nj]
                for ni in range(i - 1, i + 2)
                for nj in range(j - 1, j + 2)
                if 0 <= ni < height
                and 0 <= nj < width
                and result[ni][nj]
                not in ["Built-up", "Permanent water bodies"]
            ]

            if neighbors:
                result[i][j] = max(set(neighbors), key=neighbors.count)
                filled.append((i, j))

        for pos in filled:
            to_fill.remove(pos)

    return result


def get_biomes(lat, lon, area_size_m, pixel_size_m):
    """Fetch biome data from Copernicus."""
    token_resp = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    token = token_resp.json()["access_token"]

    lat_offset = (area_size_m[1] / 2) / 111320
    lon_offset = (area_size_m[0] / 2) / (
        111320 * abs(math.cos(math.radians(lat)))
    )
    bounds = [
        lon - lon_offset,
        lat - lat_offset,
        lon + lon_offset,
        lat + lat_offset,
    ]

    width = int(area_size_m[0] / pixel_size_m)
    height = int(area_size_m[1] / pixel_size_m)

    print(f"Requesting {width}x{height} pixels ({pixel_size_m}m per pixel)")

    payload = {
        "input": {
            "bounds": {
                "bbox": bounds,
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                },
            },
            "data": [
                {
                    "dataFilter": {
                        "timeRange": {
                            "from": "2020-01-01T00:00:00Z",
                            "to": "2020-12-31T23:59:59Z",
                        }
                    },
                    "type": "byoc-828f6b20-8ffd-48f8-a1da-fefd271456db",
                }
            ],
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [
                {"identifier": "default", "format": {"type": "image/tiff"}}
            ],
        },
        "evalscript": """
        //VERSION=3
        function setup() {
          return {input: ["LCM10"], output: {bands: 1, sampleType: "UINT8"}};
        }
        function evaluatePixel(sample) {
          return [sample.LCM10];
        }
        """,
    }

    response = requests.post(
        "https://sh.dataspace.copernicus.eu/api/v1/process",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
    )

    if response.status_code != 200:
        raise Exception(f"API error {response.status_code}")

    with rasterio.open(BytesIO(response.content)) as src:
        codes = src.read(1)

    grid = [[BIOMES.get(code, "Unknown") for code in row] for row in codes]
    grid = fill_buildup_and_water(grid)

    return grid, bounds[1], bounds[3], bounds[0], bounds[2]


def map_to_hexagons(
    lat, lon, grid, lat_min, lat_max, lon_min, lon_max, area_size_m, hex_size_m
):
    """Create hex grid and map biomes."""
    if hex_size_m >= 50:
        resolution = 10
    elif hex_size_m >= 20:
        resolution = 11
    elif hex_size_m >= 7:
        resolution = 12
    elif hex_size_m >= 2:
        resolution = 13
    else:
        resolution = 14

    center_hex = h3.latlng_to_cell(lat, lon, resolution)
    avg_hex_edge = h3.average_hexagon_edge_length(resolution, "m")
    radius_m = max(area_size_m) / 2
    rings = int(radius_m / (avg_hex_edge * 1.5)) + 1

    print(
        f"Using H3 resolution {resolution} (edge ~{avg_hex_edge:.1f}m) with {rings} rings"
    )

    hexagons = h3.grid_disk(center_hex, rings)

    height, width = len(grid), len(grid[0])
    hex_biomes = {}

    for hex_id in hexagons:
        h_lat, h_lon = h3.cell_to_latlng(hex_id)
        row = int((1 - (h_lat - lat_min) / (lat_max - lat_min)) * height)
        col = int((h_lon - lon_min) / (lon_max - lon_min) * width)
        row, col = max(0, min(height - 1, row)), max(0, min(width - 1, col))
        hex_biomes[hex_id] = grid[row][col]

    return hex_biomes


def build_hex_spatial_index(hexagons):
    """Build a spatial index for fast hex lookup."""
    hex_positions = {}
    for hex_id in hexagons:
        lat, lon = h3.cell_to_latlng(hex_id)
        hex_positions[hex_id] = (lat, lon)
    return hex_positions


def find_nearest_hex_fast(pt_lat, pt_lon, hex_positions, lat_correction):
    """Find nearest hex using pre-computed positions."""
    min_dist = float("inf")
    nearest = None

    for hex_id, (h_lat, h_lon) in hex_positions.items():
        d = ((h_lon - pt_lon) * lat_correction) ** 2 + (h_lat - pt_lat) ** 2
        if d < min_dist:
            min_dist, nearest = d, hex_id

    return nearest


def snap_rivers_to_hexes(rivers, hexagons, lat_correction):
    """Snap river lines to hexagons with proper connectivity."""
    all_lats = [h3.cell_to_latlng(h)[0] for h in hexagons]
    all_lons = [h3.cell_to_latlng(h)[1] for h in hexagons]
    lat_min, lat_max = min(all_lats), max(all_lats)
    lon_min, lon_max = min(all_lons), max(all_lons)

    hex_positions = build_hex_spatial_index(hexagons)
    water_hexes = set()

    # Get average hex edge length for adaptive interpolation
    sample_hex = list(hexagons)[0]
    resolution = h3.get_resolution(sample_hex)
    avg_hex_edge = h3.average_hexagon_edge_length(resolution, "m")

    for feature in rivers:
        coords = feature["coordinates"]

        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]

            # Check if at least one endpoint is in bounds
            pt1_in = lat_min <= lat1 <= lat_max and lon_min <= lon1 <= lon_max
            pt2_in = lat_min <= lat2 <= lat_max and lon_min <= lon2 <= lon_max

            if not (pt1_in or pt2_in):
                continue

            # Calculate segment length in meters (approximate)
            lat_avg = (lat1 + lat2) / 2
            dx = (lon2 - lon1) * 111320 * abs(math.cos(math.radians(lat_avg)))
            dy = (lat2 - lat1) * 111320
            segment_length = math.sqrt(dx**2 + dy**2)

            # Adaptive interpolation: ensure points are closer than half a hex width
            num_points = max(10, int(segment_length / (avg_hex_edge * 0.3)))

            prev_hex = None
            for j in range(num_points + 1):
                t = j / num_points
                pt_lon = lon1 + t * (lon2 - lon1)
                pt_lat = lat1 + t * (lat2 - lat1)

                if not (
                    lat_min <= pt_lat <= lat_max
                    and lon_min <= pt_lon <= lon_max
                ):
                    prev_hex = None  # Reset connection tracking
                    continue

                # Find nearest hex
                nearest = find_nearest_hex_fast(
                    pt_lat, pt_lon, hex_positions, lat_correction
                )

                if nearest:
                    water_hexes.add(nearest)

                    # Fill gaps between consecutive hexes
                    if prev_hex and prev_hex != nearest:
                        # Only bridge if hexes are reasonably close to avoid spurious long links
                        try:
                            grid_dist = h3.grid_distance(prev_hex, nearest)
                        except Exception:
                            grid_dist = None

                        if grid_dist is not None and grid_dist <= 3:
                            try:
                                bridge_hexes = h3.grid_path_cells(
                                    prev_hex, nearest
                                )
                                water_hexes.update(bridge_hexes)
                            except Exception:
                                pass

                    prev_hex = nearest

    return water_hexes


def point_in_polygon(pt_lon, pt_lat, poly_coords):
    """Ray casting algorithm for point-in-polygon test."""
    x, y = pt_lon, pt_lat
    inside = False
    n = len(poly_coords)
    p1_lon, p1_lat = poly_coords[0]

    for i in range(1, n + 1):
        p2_lon, p2_lat = poly_coords[i % n]
        if y > min(p1_lat, p2_lat):
            if y <= max(p1_lat, p2_lat):
                if x <= max(p1_lon, p2_lon):
                    if p1_lat != p2_lat:
                        xinters = (y - p1_lat) * (p2_lon - p1_lon) / (
                            p2_lat - p1_lat
                        ) + p1_lon
                    if p1_lon == p2_lon or x <= xinters:
                        inside = not inside
        p1_lon, p1_lat = p2_lon, p2_lat

    return inside


def snap_lakes_to_hexes(lakes, hexagons, lat_correction):
    """Snap lake polygons to hexagons with proper connectivity."""
    all_lats = [h3.cell_to_latlng(h)[0] for h in hexagons]
    all_lons = [h3.cell_to_latlng(h)[1] for h in hexagons]
    lat_min, lat_max = min(all_lats), max(all_lats)
    lon_min, lon_max = min(all_lons), max(all_lons)

    hex_positions = build_hex_spatial_index(hexagons)
    lake_hexes = set()

    # Get average hex edge length for adaptive interpolation
    sample_hex = list(hexagons)[0]
    resolution = h3.get_resolution(sample_hex)
    avg_hex_edge = h3.average_hexagon_edge_length(resolution, "m")

    for lake in lakes:
        if lake["type"] != "Polygon" or not lake["coordinates"]:
            continue

        rings = lake["coordinates"]
        main_ring = rings[0]
        hole_rings = rings[1:] if len(rings) > 1 else []

        # Get lake bounds
        lats = [coord[1] for coord in main_ring]
        lons = [coord[0] for coord in main_ring]
        lake_lat_min, lake_lat_max = min(lats), max(lats)
        lake_lon_min, lake_lon_max = min(lons), max(lons)

        # Skip if lake is completely outside hex grid
        if (
            lake_lat_max < lat_min
            or lake_lat_min > lat_max
            or lake_lon_max < lon_min
            or lake_lon_min > lon_max
        ):
            continue

        # Find candidate hexes
        candidates = {
            hex_id: pos
            for hex_id, pos in hex_positions.items()
            if (
                lake_lat_min <= pos[0] <= lake_lat_max
                and lake_lon_min <= pos[1] <= lake_lon_max
            )
        }

        if not candidates:
            continue

        # Helper to trace any ring (exterior or hole)
        def trace_ring(ring_coords, is_hole=False):
            nonlocal lake_hexes
            for i in range(len(ring_coords)):
                lon1, lat1 = ring_coords[i]
                lon2, lat2 = ring_coords[(i + 1) % len(ring_coords)]

                lat_avg = (lat1 + lat2) / 2
                dx = (
                    (lon2 - lon1)
                    * 111320
                    * abs(math.cos(math.radians(lat_avg)))
                )
                dy = (lat2 - lat1) * 111320
                edge_length = math.sqrt(dx**2 + dy**2)

                num_points = max(5, int(edge_length / (avg_hex_edge * 0.3)))

                prev_hex = None
                for j in range(num_points + 1):
                    t = j / num_points
                    pt_lon = lon1 + t * (lon2 - lon1)
                    pt_lat = lat1 + t * (lat2 - lat1)

                    nearest = find_nearest_hex_fast(
                        pt_lat, pt_lon, candidates, lat_correction
                    )
                    if not nearest:
                        prev_hex = None
                        continue

                    if not is_hole:
                        lake_hexes.add(nearest)

                    if prev_hex and prev_hex != nearest:
                        try:
                            grid_dist = h3.grid_distance(prev_hex, nearest)
                        except Exception:
                            grid_dist = None
                        if grid_dist is not None and grid_dist <= 3:
                            try:
                                bridge_hexes = h3.grid_path_cells(
                                    prev_hex, nearest
                                )
                                if not is_hole:
                                    lake_hexes.update(bridge_hexes)
                            except Exception:
                                pass
                    prev_hex = nearest

        # Trace outer boundary
        trace_ring(main_ring, is_hole=False)
        # Trace holes (we don't add to lake_hexes here; handled in fill exclusion)
        for hole in hole_rings:
            trace_ring(hole, is_hole=True)

        # Fill interior: inside outer ring and not inside any hole
        for hex_id, (hex_lat, hex_lon) in candidates.items():
            if hex_id in lake_hexes:
                continue
            inside_outer = point_in_polygon(hex_lon, hex_lat, main_ring)
            if not inside_outer:
                continue
            inside_hole = False
            for hole in hole_rings:
                if point_in_polygon(hex_lon, hex_lat, hole):
                    inside_hole = True
                    break
            if not inside_hole:
                lake_hexes.add(hex_id)

    return lake_hexes


def visualize_comparison(grid, hex_biomes, rivers=None, lakes=None):
    """Visualize square grid and hexagonal grid side by side."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

    # Left: Square grid
    def biome_to_rgb(biome_name):
        color_map = {
            "Tree cover": (0, 100 / 255, 0),
            "Shrubland": (1, 187 / 255, 34 / 255),
            "Grassland": (1, 1, 76 / 255),
            "Cropland": (240 / 255, 150 / 255, 1),
            "Herbaceous wetland": (0, 150 / 255, 160 / 255),
            "Mangroves": (0, 207 / 255, 117 / 255),
            "Moss and lichen": (250 / 255, 230 / 255, 160 / 255),
            "Bare/sparse vegetation": (180 / 255, 180 / 255, 180 / 255),
            "Permanent water bodies": (0, 100 / 255, 200 / 255),
            "Snow and ice": (240 / 255, 240 / 255, 240 / 255),
            "Unclassifiable": (10 / 255, 10 / 255, 10 / 255),
        }
        return color_map.get(biome_name, (0, 0, 0))

    grid_rgb = np.array(
        [[biome_to_rgb(biome) for biome in row] for row in grid]
    )
    ax1.imshow(grid_rgb, interpolation="nearest")
    ax1.set_title("Square Grid (Original Biome Data)")
    ax1.axis("off")

    # Right: Hexagonal grid
    sample_hex = list(hex_biomes.keys())[0]
    center_lat, _ = h3.cell_to_latlng(sample_hex)
    lat_corr = math.cos(math.radians(center_lat))

    # Snap water features
    river_hexes = (
        snap_rivers_to_hexes(rivers, hex_biomes.keys(), lat_corr)
        if rivers
        else set()
    )
    lake_hexes = (
        snap_lakes_to_hexes(lakes, hex_biomes.keys(), lat_corr)
        if lakes
        else set()
    )

    print(f"Rivers: {len(river_hexes)} hexes, Lakes: {len(lake_hexes)} hexes")

    patches, colors = [], []
    for hex_id, biome in hex_biomes.items():
        boundary = h3.cell_to_boundary(hex_id)
        coords = [(c[1] * lat_corr, c[0]) for c in boundary]
        patches.append(Polygon(coords, closed=True))

        if hex_id in lake_hexes:
            colors.append("#003d7a")
        elif hex_id in river_hexes:
            colors.append("#0066ff")
        else:
            colors.append(BIOME_COLORS.get(biome, "#000000"))

    collection = PatchCollection(
        patches,
        facecolors=colors,
        edgecolors="black",
        linewidths=0.1,
        alpha=0.8,
    )
    ax2.add_collection(collection)

    # Draw original water vectors for reference
    if rivers:
        print(f"Drawing {len(rivers)} river overlays...")
        for river in rivers:
            coords = river["coordinates"]
            if len(coords) > 0:
                lons = [c[0] * lat_corr for c in coords]
                lats = [c[1] for c in coords]
                ax2.plot(
                    lons,
                    lats,
                    color="cyan",
                    linewidth=1.5,
                    alpha=0.7,
                    zorder=10,
                )
    else:
        print("No rivers to draw")

    if lakes:
        print(f"Drawing {len(lakes)} lake overlays...")
        for lake in lakes:
            if lake["coordinates"]:
                ring = lake["coordinates"][0]
                if len(ring) > 0:
                    coords = [(c[0] * lat_corr, c[1]) for c in ring]
                    lake_poly = Polygon(
                        coords,
                        closed=True,
                        facecolor="none",
                        edgecolor="cyan",
                        linewidth=1.5,
                        alpha=0.7,
                        zorder=10,
                    )
                    ax2.add_patch(lake_poly)
    else:
        print("No lakes to draw")

    # Calculate hex bounds for proper zoom
    all_lons = []
    all_lats = []
    for hex_id in hex_biomes.keys():
        boundary = h3.cell_to_boundary(hex_id)
        for coord in boundary:
            all_lons.append(coord[1] * lat_corr)
            all_lats.append(coord[0])

    hex_lon_min, hex_lon_max = min(all_lons), max(all_lons)
    hex_lat_min, hex_lat_max = min(all_lats), max(all_lats)

    lon_padding = (hex_lon_max - hex_lon_min) * 0.05
    lat_padding = (hex_lat_max - hex_lat_min) * 0.05

    ax2.set_xlim(hex_lon_min - lon_padding, hex_lon_max + lon_padding)
    ax2.set_ylim(hex_lat_min - lat_padding, hex_lat_max + lat_padding)
    ax2.set_aspect("equal")
    ax2.set_xlabel("Longitude (corrected)")
    ax2.set_ylabel("Latitude")
    ax2.set_title(
        f"Hexagonal Grid ({len(hex_biomes)} hexagons) with Water Features"
    )

    plt.tight_layout()
    plt.show()


def export_to_json(
    hex_biomes,
    river_hexes,
    lake_hexes,
    filename="hex_biomes.json",
    include_boundary=False,
):
    """Export hex data to JSON including water features.

    When include_boundary is True, each record contains the polygon boundary
    coordinates for the hex. Defaults to False to keep the JSON small.
    """
    data = []
    for hid, biome in hex_biomes.items():
        lat, lon = h3.cell_to_latlng(hid)
        record = {
            "hex_id": hid,
            "lat": lat,
            "lon": lon,
            "biome": biome,
            "is_river": hid in river_hexes,
            "is_lake": hid in lake_hexes,
        }
        if include_boundary:
            record["boundary"] = [
                [c[0], c[1]] for c in h3.cell_to_boundary(hid)
            ]
        data.append(record)

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Exported to {filename}")
    print(f"  Total hexes: {len(data)}")
    print(f"  River hexes: {len(river_hexes)}")
    print(f"  Lake hexes: {len(lake_hexes)}")


if __name__ == "__main__":
    print("Configuration:")
    print(f"  Location: ({CENTER_LAT}, {CENTER_LON})")
    print(f"  Area: {AREA_SIZE_M[0] / 1000}km x {AREA_SIZE_M[1] / 1000}km")
    print(f"  Hex size: {HEX_SIZE_M}m")
    print()

    t0 = time.perf_counter()
    print("Fetching biome data...")
    grid, lat_min, lat_max, lon_min, lon_max = get_biomes(
        CENTER_LAT, CENTER_LON, AREA_SIZE_M, HEX_SIZE_M
    )
    t1 = time.perf_counter()

    print("Fetching river features from EU-Hydro...")
    rivers = get_euhydro_rivers(lat_min, lat_max, lon_min, lon_max)
    t2 = time.perf_counter()
    print("Fetching lake/waterbody polygons from EU-Hydro...")
    lakes = get_euhydro_lakes(lat_min, lat_max, lon_min, lon_max)
    t3 = time.perf_counter()

    print("Creating hexagonal grid...")
    hex_biomes = map_to_hexagons(
        CENTER_LAT,
        CENTER_LON,
        grid,
        lat_min,
        lat_max,
        lon_min,
        lon_max,
        AREA_SIZE_M,
        HEX_SIZE_M,
    )
    t4 = time.perf_counter()

    # Snap water features to hexagons
    sample_hex = list(hex_biomes.keys())[0]
    center_lat, _ = h3.cell_to_latlng(sample_hex)
    lat_corr = math.cos(math.radians(center_lat))

    print("Snapping rivers to hexagons...")
    river_hexes = (
        snap_rivers_to_hexes(rivers, hex_biomes.keys(), lat_corr)
        if rivers
        else set()
    )
    t5 = time.perf_counter()
    print(f">>> SNAPPED {len(river_hexes)} RIVER HEXES <<<")

    print("Snapping lakes to hexagons...")
    lake_hexes = (
        snap_lakes_to_hexes(lakes, hex_biomes.keys(), lat_corr)
        if lakes
        else set()
    )
    t6 = time.perf_counter()
    print(f">>> SNAPPED {len(lake_hexes)} LAKE HEXES <<<")

    print("\nData preparation timings (seconds):")
    print(f"  Biomes:    {t1 - t0:.2f}")
    print(f"  Rivers:    {t2 - t1:.2f}")
    print(f"  Lakes:     {t3 - t2:.2f}")
    print(f"  Hex map:   {t4 - t3:.2f}")
    print(f"  Snap rivers: {t5 - t4:.2f}")
    print(f"  Snap lakes:  {t6 - t5:.2f}")
    print(f"  Total: {t6 - t0:.2f}")

    print("\nVisualizing...")
    visualize_comparison(grid, hex_biomes, rivers, lakes)

    print("\nExporting...")
    export_to_json(hex_biomes, river_hexes, lake_hexes, include_boundary=True)

    print("\n" + "=" * 60)
    print("DONE! Check hex_biomes.json")
    print(f"Total: {len(hex_biomes)} hexes")
    print(f"Rivers: {len(river_hexes)} hexes")
    print(f"Lakes: {len(lake_hexes)} hexes")
    print("=" * 60)
