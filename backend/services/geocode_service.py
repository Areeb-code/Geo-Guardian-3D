import requests

def resolve_location(query: str) -> dict:
    """Resolves any city, district, or province name worldwide into a bounding box."""
    clean_query = query.strip()
    if clean_query.lower() in ("lahore", "lahore district"):
        return {
            "name": "Lahore District, Pakistan",
            "bbox": [74.10, 31.30, 74.55, 31.68],
            "center": [74.325, 31.49]
        }

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": clean_query,
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "GeoGuardian3D/2.0"}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    results = resp.json()

    if not results:
        raise ValueError(f"Location '{query}' not found.")

    item = results[0]
    # Nominatim returns [south_lat, north_lat, west_lon, east_lon]
    south, north, west, east = map(float, item["boundingbox"])

    # Cap max span to ~1.2 degrees (~130 km) so GEE area reduction stays fast (< 8 sec)
    lon_center = (west + east) / 2.0
    lat_center = (south + north) / 2.0
    half_lon = min((east - west) / 2.0, 0.6)
    half_lat = min((north - south) / 2.0, 0.6)

    bbox = [
        round(lon_center - half_lon, 4),
        round(lat_center - half_lat, 4),
        round(lon_center + half_lon, 4),
        round(lat_center + half_lat, 4),
    ]

    return {
        "name": item.get("display_name", clean_query).split(",")[0] + ", " + item.get("display_name", "").split(",")[-1].strip(),
        "bbox": bbox,
        "center": [round(lon_center, 4), round(lat_center, 4)]
    }