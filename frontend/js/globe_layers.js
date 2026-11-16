let viewer = null;
const activeGEE = {};
let isTilted = false;

export function initGlobe() {
  try {
    viewer = new Cesium.Viewer('cesiumContainer', {
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      requestRenderMode: false,
      contextOptions: {
        webgl: {
          alpha: false,
          antialias: true,
          powerPreference: 'high-performance',
          failIfMajorPerformanceCaveat: false,
        },
      },
      baseLayer: false,
    });

    // Add free Esri World Satellite base imagery safely
    Cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
    )
      .then((provider) => {
        if (viewer) viewer.imageryLayers.addImageryProvider(provider, 0);
      })
      .catch(() => {
        // Fallback to OpenStreetMap if ArcGIS is unreachable
        if (viewer) {
          viewer.imageryLayers.addImageryProvider(
            new Cesium.UrlTemplateImageryProvider({
              url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            }),
            0
          );
        }
      });

    viewer.scene.globe.enableLighting = false;
    if (viewer.scene.skyAtmosphere) viewer.scene.skyAtmosphere.show = true;
    viewer.scene.fog.enabled = true;

    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(74.325, 31.49, 12000000.0),
    });

    return viewer;
  } catch (err) {
    console.error('Cesium WebGL initialization error:', err);
    return null;
  }
}

export function flyToAOI(centerLonLat, tilted = false) {
  if (!viewer || !centerLonLat) return;
  const [lon, lat] = centerLonLat;
  isTilted = tilted;

  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(
      lon,
      tilted ? lat - 0.22 : lat,
      tilted ? 26000.0 : 48000.0
    ),
    orientation: {
      heading: Cesium.Math.toRadians(0.0),
      pitch: Cesium.Math.toRadians(tilted ? -42.0 : -90.0),
      roll: 0.0,
    },
    duration: 2.2,
    easingFunction: Cesium.EasingFunction.CUBIC_IN_OUT,
  });
}

export function toggleHorizonTilt(centerLonLat) {
  flyToAOI(centerLonLat, !isTilted);
}

export function updateGEELayers(tiles) {
  if (!viewer) return;

  Object.values(activeGEE).forEach((layer) => {
    if (layer) viewer.imageryLayers.remove(layer, true);
  });

  const addXYZ = (key, url, show, alpha) => {
    if (!url) {
      activeGEE[key] = null;
      return;
    }
    const provider = new Cesium.UrlTemplateImageryProvider({
      url: url,
      maximumLevel: 16,
    });
    const layer = viewer.imageryLayers.addImageryProvider(provider);
    layer.show = show;
    layer.alpha = alpha;
    activeGEE[key] = layer;
  };

  addXYZ('rgb_a', tiles.rgb_a, document.getElementById('toggle-rgb-a').checked, parseFloat(document.getElementById('alpha-rgb-a').value));
  addXYZ('rgb_b', tiles.rgb_b, document.getElementById('toggle-rgb-b').checked, parseFloat(document.getElementById('alpha-rgb-b').value));
  addXYZ('class_b', tiles.class_b, document.getElementById('toggle-class-b').checked, parseFloat(document.getElementById('alpha-class-b').value));
  addXYZ('smog_b', tiles.smog_b, document.getElementById('toggle-smog-b').checked, parseFloat(document.getElementById('alpha-smog-b').value));
  addXYZ('change', tiles.change, document.getElementById('toggle-change').checked, parseFloat(document.getElementById('alpha-change').value));
}

export function bindLayerControls() {
  const mappings = [
    ['rgb_b', 'toggle-rgb-b', 'alpha-rgb-b'],
    ['rgb_a', 'toggle-rgb-a', 'alpha-rgb-a'],
    ['change', 'toggle-change', 'alpha-change'],
    ['class_b', 'toggle-class-b', 'alpha-class-b'],
    ['smog_b', 'toggle-smog-b', 'alpha-smog-b'],
  ];

  mappings.forEach(([key, toggleId, sliderId]) => {
    const toggle = document.getElementById(toggleId);
    const slider = document.getElementById(sliderId);

    toggle.addEventListener('change', () => {
      if (activeGEE[key]) activeGEE[key].show = toggle.checked;
    });

    slider.addEventListener('input', () => {
      if (activeGEE[key]) activeGEE[key].alpha = parseFloat(slider.value);
    });
  });
}