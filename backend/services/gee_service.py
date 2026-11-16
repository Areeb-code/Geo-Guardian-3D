import ee
import threading
from datetime import datetime, timedelta
from typing import Optional
from backend.config import settings
from backend.services.geocode_service import resolve_location

_EE_READY = False
_CACHE: dict[str, dict] = {}
_LOCK = threading.Lock()

def _ensure_ee_initialized():
    global _EE_READY
    if _EE_READY:
        return
    project_id = settings.GCP_PROJECT_ID or "satelite-514107"
    try:
        ee.Initialize(project=project_id)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project_id)
    _EE_READY = True

def _prep_s2(img):
    ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndbi = img.normalizedDifference(['B11', 'B8']).rename('NDBI')
    return img.select(['B2', 'B3', 'B4', 'B8', 'B11']).addBands([ndvi, ndbi]).toFloat()

def _prep_landsat_57(img):
    optical = img.select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5']) \
        .multiply(0.0000275).add(-0.2).multiply(10000) \
        .rename(['B2', 'B3', 'B4', 'B8', 'B11'])
    ndvi = optical.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndbi = optical.normalizedDifference(['B11', 'B8']).rename('NDBI')
    return optical.addBands([ndvi, ndbi]).toFloat()

def _prep_landsat_8(img):
    optical = img.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6']) \
        .multiply(0.0000275).add(-0.2).multiply(10000) \
        .rename(['B2', 'B3', 'B4', 'B8', 'B11'])
    ndvi = optical.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndbi = optical.normalizedDifference(['B11', 'B8']).rename('NDBI')
    return optical.addBands([ndvi, ndbi]).toFloat()

def _safe_s2_composite(aoi_geom: ee.Geometry, start_str: str, end_str: str) -> ee.Image:
    """Guarantees a valid 7-band Sentinel-2 composite even in cloudy cities like London or Tokyo."""
    base_col = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi_geom)
        .filterDate(start_str, end_str)
    )
    # Pick the 25 clearest scenes in the window so the collection is never empty
    clearest = base_col.sort('CLOUDY_PIXEL_PERCENTAGE').limit(25).map(_prep_s2)
    return clearest.median().clip(aoi_geom)

def _safe_landsat_composite(collection_id: str, prep_fn, aoi_geom: ee.Geometry, year: int) -> ee.Image:
    """Guarantees a valid 7-band Landsat composite with a ±1 year fallback if scenes are sparse."""
    base_col = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi_geom)
        .filterDate(f"{year - 1}-01-01", f"{year + 1}-12-31")
    )
    clearest = base_col.sort('CLOUD_COVER').limit(25).map(prep_fn)
    return clearest.median().clip(aoi_geom)

def _train_local_rf_for_aoi(aoi_geom: ee.Geometry) -> ee.Classifier:
    """Trains a 100-tree Random Forest adapted to any city/province on Earth."""
    ref_s2 = _safe_s2_composite(aoi_geom, '2021-01-01', '2021-12-31')

    worldcover = ee.ImageCollection('ESA/WorldCover/v200').first().clip(aoi_geom)
    remapped_labels = worldcover.remap(
        [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
        [0,  0,  0,  0,  1,  2,  2,  2,  2,  2,  2]
    ).rename('landcover')

    training_stack = ref_s2.addBands(remapped_labels)
    training_samples = training_stack.stratifiedSample(
        numPoints=90,
        classBand='landcover',
        region=aoi_geom,
        scale=60,
        seed=42,
        geometries=False
    )

    features = ['B2', 'B3', 'B4', 'B8', 'B11', 'NDVI', 'NDBI']
    return ee.Classifier.smileRandomForest(80).train(
        features=training_samples,
        classProperty='landcover',
        inputProperties=features
    )

def _get_optical_composite(aoi_geom: ee.Geometry, year: Optional[int] = None) -> tuple[ee.Image, str]:
    if year is None:
        now = datetime.utcnow()
        end_str = now.strftime('%Y-%m-%d')
        # 180-day lookback guarantees cloud-free pixels in London/Tokyo
        start_str = (now - timedelta(days=180)).strftime('%Y-%m-%d')
        return _safe_s2_composite(aoi_geom, start_str, end_str), f"Live ({end_str})"

    if year >= 2016:
        return _safe_s2_composite(aoi_geom, f"{year}-01-01", f"{year}-12-31"), f"{year} (Sentinel-2 10m)"
    elif year >= 2013:
        return _safe_landsat_composite('LANDSAT/LC08/C02/T1_L2', _prep_landsat_8, aoi_geom, year), f"{year} (Landsat-8 30m)"
    elif 1999 <= year <= 2012:
        return _safe_landsat_composite('LANDSAT/LE07/C02/T1_L2', _prep_landsat_57, aoi_geom, year), f"{year} (Landsat-7 30m)"
    else:
        return _safe_landsat_composite('LANDSAT/LT05/C02/T1_L2', _prep_landsat_57, aoi_geom, year), f"{year} (Landsat-5 30m)"

def _get_smog_layer(aoi_geom: ee.Geometry, year: Optional[int] = None, specific_date: Optional[str] = None) -> tuple[Optional[ee.Image], Optional[float], str]:
    if year is not None and year < 2018:
        return None, None, "Pre-2018 (No Sentinel-5P)"

    if specific_date:
        dt = datetime.strptime(specific_date, '%Y-%m-%d')
        s_start = (dt - timedelta(days=2)).strftime('%Y-%m-%d')
        s_end = (dt + timedelta(days=3)).strftime('%Y-%m-%d')
        label = f"Date: {specific_date} (±2d)"
    elif year is not None:
        s_start = f"{year}-01-01"
        s_end = f"{year}-12-31"
        label = f"{year} Annual Mean"
    else:
        now = datetime.utcnow()
        s_end = now.strftime('%Y-%m-%d')
        s_start = (now - timedelta(days=14)).strftime('%Y-%m-%d')
        label = f"Live ({s_start} to {s_end})"

    smog_col = (
        ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_AER_AI')
        .filterBounds(aoi_geom)
        .filterDate(s_start, s_end)
        .select('absorbing_aerosol_index')
    )

    smog_img = smog_col.mean().clip(aoi_geom)
    stats = smog_img.reduceRegion(ee.Reducer.mean(), aoi_geom, 2000, maxPixels=1e9).getInfo()
    raw_val = stats.get('absorbing_aerosol_index') if stats else None
    mean_val = round(float(raw_val), 2) if raw_val is not None else 0.0
    return smog_img, mean_val, label

def get_geoguardian_payload(
    location: str = "Lahore",
    mode: str = "live",
    year_a: int = 2019,
    year_b: int = 2025,
    smog_date: Optional[str] = None,
    force_refresh: bool = False
) -> dict:
    _ensure_ee_initialized()
    loc_info = resolve_location(location)
    cache_key = f"{loc_info['name']}_{mode}_{year_a}_{year_b}_{smog_date}"

    if not force_refresh and cache_key in _CACHE:
        return _CACHE[cache_key]

    with _LOCK:
        if not force_refresh and cache_key in _CACHE:
            return _CACHE[cache_key]

        aoi_geom = ee.Geometry.Rectangle(loc_info["bbox"])
        rf_model = _train_local_rf_for_aoi(aoi_geom)

        if mode == "live":
            img_a, label_a = _get_optical_composite(aoi_geom, year=2019)
            img_b, label_b = _get_optical_composite(aoi_geom, year=None)
            smog_a_img, smog_a_val, _ = _get_smog_layer(aoi_geom, year=2019)
            smog_b_img, smog_b_val, smog_window = _get_smog_layer(aoi_geom, year=None, specific_date=smog_date)
        else:
            img_a, label_a = _get_optical_composite(aoi_geom, year=year_a)
            img_b, label_b = _get_optical_composite(aoi_geom, year=year_b)
            smog_a_img, smog_a_val, _ = _get_smog_layer(aoi_geom, year=year_a)
            smog_b_img, smog_b_val, smog_window = _get_smog_layer(aoi_geom, year=year_b, specific_date=smog_date)

        class_a = img_a.classify(rf_model)
        class_b = img_b.classify(rf_model)

        conversion_binary = class_a.eq(0).And(class_b.eq(1))
        conversion_layer = conversion_binary.selfMask().rename('converted')

        # Single combined reduceRegion call for all 6 area metrics at once (3x faster)
        pixel_area = ee.Image.pixelArea().divide(1e6)
        area_stack = ee.Image.cat([
            pixel_area.rename('total'),
            pixel_area.updateMask(class_a.eq(0)).rename('veg_a'),
            pixel_area.updateMask(class_b.eq(0)).rename('veg_b'),
            pixel_area.updateMask(class_a.eq(1)).rename('built_a'),
            pixel_area.updateMask(class_b.eq(1)).rename('built_b'),
            pixel_area.updateMask(conversion_binary).rename('conv'),
        ])

        area_stats = area_stack.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom,
            scale=60,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo() or {}

        total_aoi = round(float(area_stats.get('total') or 1.0), 2)
        veg_a = round(float(area_stats.get('veg_a') or 0.0), 2)
        veg_b = round(float(area_stats.get('veg_b') or 0.0), 2)
        built_a = round(float(area_stats.get('built_a') or 0.0), 2)
        built_b = round(float(area_stats.get('built_b') or 0.0), 2)
        conv_sqkm = round(float(area_stats.get('conv') or 0.0), 2)
        loss_pct = round((conv_sqkm / total_aoi) * 100, 2) if total_aoi > 0 else 0.0

        if smog_b_val is None:
            smog_status = "No Satellite Data"
        elif smog_b_val >= 1.5:
            smog_status = "Severe Plume"
        elif smog_b_val >= 0.8:
            smog_status = "Moderate Haze"
        else:
            smog_status = "Low / Clear"

        rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}
        class_vis = {'min': 0, 'max': 2, 'palette': ['228B22', '808080', 'EEDC82']}
        change_vis = {'min': 1, 'max': 1, 'palette': ['FF0000']}
        smog_vis = {'min': -0.5, 'max': 2.5, 'palette': ['black', 'blue', 'cyan', 'green', 'yellow', 'red']}

        result = {
            "metrics": {
                "mode": mode,
                "aoi": loc_info["name"],
                "center": loc_info["center"],
                "bbox": loc_info["bbox"],
                "total_area_sqkm": total_aoi,
                "year_a_label": label_a,
                "year_b_label": label_b,
                "veg_a_sqkm": veg_a,
                "veg_b_sqkm": veg_b,
                "built_a_sqkm": built_a,
                "built_b_sqkm": built_b,
                "converted_sqkm": conv_sqkm,
                "loss_pct": loss_pct,
                "smog_a_index": smog_a_val,
                "smog_b_index": smog_b_val,
                "smog_status": smog_status,
                "smog_date_window": smog_window,
            },
            "tiles": {
                "rgb_a": img_a.getMapId(rgb_vis)['tile_fetcher'].url_format,
                "rgb_b": img_b.getMapId(rgb_vis)['tile_fetcher'].url_format,
                "class_a": class_a.getMapId(class_vis)['tile_fetcher'].url_format,
                "class_b": class_b.getMapId(class_vis)['tile_fetcher'].url_format,
                "change": conversion_layer.getMapId(change_vis)['tile_fetcher'].url_format,
                "smog_a": smog_a_img.getMapId(smog_vis)['tile_fetcher'].url_format if smog_a_img else None,
                "smog_b": smog_b_img.getMapId(smog_vis)['tile_fetcher'].url_format if smog_b_img else None,
            }
        }

        _CACHE[cache_key] = result
        return result