const leadForm        = document.getElementById('lead-form');
const resultsCard     = document.getElementById('results-card');
const resultsContent  = document.getElementById('results-content');
const loadingIndicator = document.getElementById('loading-indicator');
const submitBtn       = document.getElementById('submit-btn');
const testProfileSel  = document.getElementById('test-profile');

// ── API Toggle state ────────────────────────────────────────────────────────
const apiState = { census: true, fred: true, wikipedia: true, news: true, walkscore: true, intellipins: true, google: true, osm: true, open_meteo: true, crime: true };

document.querySelectorAll('[data-api]').forEach(btn => {
    btn.classList.add('on');
    btn.addEventListener('click', () => {
        const api = btn.dataset.api;
        apiState[api] = !apiState[api];
        btn.classList.toggle('on',  apiState[api]);
        btn.classList.toggle('off', !apiState[api]);
    });
});

function enabledApis() {
    return Object.entries(apiState).filter(([, on]) => on).map(([api]) => api);
}

// ── LLM provider toggle ─────────────────────────────────────────────────────
let llmProvider = 'anthropic';

document.querySelectorAll('[data-llm]').forEach(btn => {
    btn.addEventListener('click', () => {
        llmProvider = btn.dataset.llm;
        document.querySelectorAll('[data-llm]').forEach(b => {
            b.classList.toggle('on',  b.dataset.llm === llmProvider);
            b.classList.toggle('off', b.dataset.llm !== llmProvider);
        });
    });
});

// ── Current test-profile id (null when using manual entry) ──────────────────
let currentTestProfileId = null;

// ── Test profile dropdown ───────────────────────────────────────────────────
fetch('/test_data.json')
    .then(r => r.json())
    .then(profiles => {
        profiles.forEach((p, i) => {
            const opt = document.createElement('option');
            opt.value = i;
            opt.textContent = p.label;
            testProfileSel.appendChild(opt);
        });

        testProfileSel.addEventListener('change', () => {
            if (testProfileSel.value === '') { currentTestProfileId = null; return; }
            const p = profiles[parseInt(testProfileSel.value)];
            currentTestProfileId = p.id != null ? String(p.id) : null;
            document.getElementById('name').value             = p.name;
            document.getElementById('email').value            = p.email;
            document.getElementById('company').value          = p.company;
            document.getElementById('property_address').value = p.property_address;
            document.getElementById('city').value             = p.city;
            document.getElementById('state').value            = p.state;
        });
    })
    .catch(() => {/* test_data.json missing — silent fail */});

// ── Form submit ─────────────────────────────────────────────────────────────
leadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        id:               currentTestProfileId,
        name:             document.getElementById('name').value,
        company:          document.getElementById('company').value,
        property_address: document.getElementById('property_address').value,
        city:             document.getElementById('city').value,
        state:            document.getElementById('state').value,
        email:            document.getElementById('email').value,
        enabled_apis:     enabledApis(),
        llm_provider:     llmProvider,
    };

    resultsCard.classList.add('visible');
    loadingIndicator.style.display = 'block';
    resultsContent.innerHTML = '';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Enriching...';

    try {
        const response = await fetch('http://localhost:8000/enrich', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData),
        });

        if (!response.ok) throw new Error('Enrichment failed');
        displayResults(await response.json());
    } catch (error) {
        resultsContent.innerHTML = `<p style="color: #ef4444;">Error: ${error.message}. Make sure the backend is running.</p>`;
    } finally {
        loadingIndicator.style.display = 'none';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enrich Lead Data';
    }
});

// ── Render helpers ──────────────────────────────────────────────────────────
const DISABLED_VALUE = `<span class="disabled-badge">disabled</span>`;

function metric(label, value, apiSource) {
    return `
        <div class="metric" data-source="${apiSource}">
            <span class="metric-label">${label}</span>
            <span class="metric-value">${value}</span>
        </div>`;
}

function disabledMetric(label) {
    return `
        <div class="metric">
            <span class="metric-label">${label}</span>
            <span class="metric-value" style="font-size:0.85rem;">${DISABLED_VALUE}</span>
        </div>`;
}

function renderWikiSection(wikipedia) {
    if (wikipedia?._disabled) {
        return `<div style="margin-top:1.5rem;">
            <h3 style="font-size:1rem;margin-bottom:0.5rem;">Wikipedia</h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">${DISABLED_VALUE} Wikipedia API is off.</p>
        </div>`;
    }
    if (!wikipedia) return '';

    const wikiTag = `<span style="font-size:0.65rem;font-weight:400;background:rgba(99,102,241,0.15);color:#818cf8;padding:0.1rem 0.4rem;border-radius:999px;margin-left:0.4rem;vertical-align:middle;">Wikipedia</span>`;

    let html = '';

    if (wikipedia.company) {
        const { extract, url } = wikipedia.company;
        html += `
        <div style="margin-top:1.5rem;">
            <h3 style="font-size:1rem;margin-bottom:0.5rem;">
                About the Company ${wikiTag}
            </h3>
            <p style="font-size:0.875rem;line-height:1.6;color:var(--text-muted);">${extract}</p>
            ${url ? `<a href="${safeHref(url)}" target="_blank" rel="noopener noreferrer"
                style="font-size:0.72rem;color:#818cf8;text-decoration:none;display:inline-block;margin-top:0.4rem;">
                Read more on Wikipedia →
            </a>` : ''}
        </div>`;
    }

    if (wikipedia.city?.extract) {
        html += `
        <div style="margin-top:1.25rem;">
            <h3 style="font-size:1rem;margin-bottom:0.5rem;">
                ${wikipedia.city.title} ${wikiTag}
            </h3>
            <p style="font-size:0.875rem;line-height:1.6;color:var(--text-muted);">${wikipedia.city.extract}</p>
        </div>`;
    }

    return html;
}

function renderCensusMetrics(census) {
    if (census?._disabled) {
        return `<div class="metric-grid" style="margin-top:1.5rem;">
            ${disabledMetric('Population')}
            ${disabledMetric('Median Income')}
            ${disabledMetric('Renter %')}
        </div>`;
    }
    return `<div class="metric-grid" style="margin-top:1.5rem;">
        ${metric('Population',     census.population      || 'N/A', 'US Census Bureau ACS')}
        ${metric('Median Income',  census.median_income   || 'N/A', 'US Census Bureau ACS')}
        ${metric('Renter %',       census.renter_percentage || 'N/A', 'US Census Bureau ACS')}
    </div>`;
}

function renderFredMetrics(fred) {
    if (fred?._disabled) {
        return `<div class="metric-grid" style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            ${disabledMetric('Vacancy Rate')}
        </div>`;
    }
    return `<div class="metric-grid" style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
        ${metric('Vacancy Rate', fred.vacancy_rate || 'N/A', 'FRED — Federal Reserve')}
    </div>`;
}

function renderWalkScore(ws) {
    if (ws?._disabled) {
        return `<div class="metric-grid" style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            ${disabledMetric('Walk Score')}
            ${disabledMetric('Transit Score')}
            ${disabledMetric('Bike Score')}
        </div>`;
    }
    if (!ws || ws.walk_score === undefined) return '';

    const score = ws.walk_score;
    let scoreColor = '#10b981';
    if (typeof score === 'number') {
        if (score < 50) scoreColor = '#ef4444';
        else if (score < 70) scoreColor = '#f59e0b';
    }
    const scoreVal = `<span style="color:${scoreColor}">${score}</span>${ws.description ? ` <small style="font-size:0.6rem;color:var(--text-muted)">${ws.description}</small>` : ''}`;

    return `<div class="metric-grid" style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
        ${metric('Walk Score',    scoreVal,               'Walk Score API')}
        ${ws.transit_score !== undefined ? metric('Transit Score', ws.transit_score, 'Walk Score API') : ''}
        ${ws.bike_score    !== undefined ? metric('Bike Score',    ws.bike_score,    'Walk Score API') : ''}
    </div>`;
}

function renderIntelliPins(ipins) {
    const tag = `<span style="font-size:0.65rem;font-weight:400;background:rgba(251,191,36,0.15);color:#fbbf24;padding:0.1rem 0.4rem;border-radius:999px;margin-left:0.4rem;vertical-align:middle;">Intellipins</span>`;
    const src = 'Intellipins';
    const sectionStyle = 'border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;';
    const subheadStyle = 'font-size:0.75rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px dashed var(--glass-border);padding-bottom:0.3rem;margin:0 0 0.6rem;';

    if (ipins?._disabled) {
        return `<div style="${sectionStyle}">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Property Intelligence ${tag}</h3>
            <div class="metric-grid">
                ${disabledMetric('Building Type')}${disabledMetric('Address Type')}${disabledMetric('Match Score')}
                ${disabledMetric('Lot Area')}${disabledMetric('Elevation')}${disabledMetric('Owner')}
            </div>
        </div>`;
    }

    if (!ipins || ipins.error) {
        return `<div style="${sectionStyle}">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Property Intelligence ${tag}</h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">${ipins?.error || 'No data'}</p>
        </div>`;
    }

    const val = v => (v != null && v !== 'N/A' && v !== '') ? v : 'N/A';

    const scoreColor = ipins.geocode_score >= 0.9 ? '#10b981' : ipins.geocode_score >= 0.7 ? '#f59e0b' : '#ef4444';
    const scoreVal   = ipins.geocode_score != null
        ? `<span style="color:${scoreColor};font-weight:700;">${(ipins.geocode_score * 100).toFixed(0)}%</span>`
        : 'N/A';

    const coords = (ipins.lat != null && ipins.lon != null)
        ? `${parseFloat(ipins.lat).toFixed(5)}, ${parseFloat(ipins.lon).toFixed(5)}`
        : 'N/A';

    const parcel  = ipins.parcel || {};
    const hasParcel = Object.keys(parcel).length > 0;

    const buildingTypeColor = ipins.building_type === 'Single Family Housing' ? '#34d399' : '#f59e0b';

    return `<div style="${sectionStyle}">
        <h3 style="font-size:0.9rem;margin-bottom:1rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Property Intelligence ${tag}</h3>

        <h4 style="${subheadStyle}">Address Verification</h4>
        <div class="metric-grid" style="margin-bottom:1.25rem;">
            ${metric('Building Type', `<span style="color:${buildingTypeColor};font-weight:600;">${val(ipins.building_type)}</span>`, src)}
            ${metric('Address Type',  val(ipins.address_type),  src)}
            ${metric('Match Score',   scoreVal,                  src)}
            <div class="metric" style="grid-column:span 3;" data-source="${src}">
                <span class="metric-label">Verified Address</span>
                <span class="metric-value" style="font-size:0.8rem;">${val(ipins.formatted_address)}</span>
            </div>
        </div>

        <h4 style="${subheadStyle}">Geolocation <small style="font-size:0.65rem;color:#fbbf24;text-transform:none;font-weight:400;">(source: Intellipins)</small></h4>
        <div class="metric-grid" style="margin-bottom:1.25rem;">
            ${metric('Lat / Lon', coords,              src)}
            ${metric('IPINS ID',  val(ipins.ipins_id), src)}
        </div>

        ${hasParcel ? `
        <h4 style="${subheadStyle}">Parcel Data</h4>
        <div class="metric-grid">
            ${metric('Lot Area',    val(parcel.area_sqft),   'Intellipins Parcel')}
            ${metric('Lot Area m²', val(parcel.area_sqm),    'Intellipins Parcel')}
            ${metric('Elevation',   parcel.elevation_m !== 'N/A' ? parcel.elevation_m + ' m' : 'N/A', 'Intellipins Parcel')}
            ${metric('Owner',       val(parcel.parcel_owner), 'Intellipins Parcel')}
            ${metric('APN',         val(parcel.apn),          'Intellipins Parcel')}
            ${metric('Parcel ID',   val(parcel.iparcel_id),   'Intellipins Parcel')}
        </div>
        ` : '<p style="font-size:0.75rem;color:var(--text-muted);font-style:italic;">Parcel data unavailable for this address.</p>'}
    </div>`;
}

function renderOSM(osm, parcel = null) {
    const osmTag = `<span style="font-size:0.65rem;font-weight:400;background:rgba(34,197,94,0.15);color:#22c55e;padding:0.1rem 0.4rem;border-radius:999px;margin-left:0.4rem;vertical-align:middle;">OSM</span>`;
    const src = 'OpenStreetMap & Overpass';

    if (osm?._disabled) {
        return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                OSM Property Info ${osmTag}
            </h3>
            <div class="metric-grid">
                ${disabledMetric('Type')}${disabledMetric('Class')}
            </div>
        </div>`;
    }
    
    if (!osm || osm.osm_type === "N/A") {
        return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                OSM Property Info ${osmTag}
            </h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">No data</p>
        </div>`;
    }

    const coords = osm.lat !== "N/A" ? `${parseFloat(osm.lat).toFixed(4)}, ${parseFloat(osm.lon).toFixed(4)}` : "N/A";
    const bd = osm.building_details || {};
    
    const val = (v) => (v && v !== "N/A") ? v : "N/A";
    
    function renderFootprintSvg(wkt, parcel) {
        console.log('[footprint] parcel:', parcel, '| geometry:', parcel?.geometry);
        // Parse building WKT into [lon, lat] points
        let bldPoints = null;
        if (wkt && wkt !== 'N/A' && (wkt.startsWith('POLYGON') || wkt.startsWith('MULTIPOLYGON'))) {
            try {
                const m = wkt.match(/\(\((.*?)\)\)/);
                if (m) {
                    bldPoints = m[1].split(',').map(pair => {
                        const [lon, lat] = pair.trim().split(/\s+/).map(Number);
                        return [lon, lat];
                    });
                }
            } catch (_) {}
        }

        // Parse parcel geometry — handles GeoJSON Geometry, Feature, FeatureCollection, or WKT string
        let parcelPoints = null;
        let rawGeom = parcel?.geometry;
        if (rawGeom) {
            try {
                // Unwrap Feature / FeatureCollection
                if (rawGeom.type === 'Feature') rawGeom = rawGeom.geometry;
                else if (rawGeom.type === 'FeatureCollection') rawGeom = rawGeom.features?.[0]?.geometry;

                if (rawGeom?.type === 'Polygon') {
                    parcelPoints = rawGeom.coordinates[0].map(([lon, lat]) => [lon, lat]);
                } else if (rawGeom?.type === 'MultiPolygon') {
                    parcelPoints = rawGeom.coordinates[0][0].map(([lon, lat]) => [lon, lat]);
                } else if (typeof rawGeom === 'string' &&
                           (rawGeom.startsWith('POLYGON') || rawGeom.startsWith('MULTIPOLYGON'))) {
                    // WKT fallback
                    const m = rawGeom.match(/\(\((.*?)\)\)/);
                    if (m) parcelPoints = m[1].split(',').map(pair => {
                        const [lon, lat] = pair.trim().split(/\s+/).map(Number);
                        return [lon, lat];
                    });
                } else {
                    console.warn('[footprint] unrecognised parcel geometry format:', rawGeom);
                }
            } catch (e) { console.warn('[footprint] parcel parse error:', e); }
        }

        if (!bldPoints && !parcelPoints) return wkt || 'N/A';

        // Compute unified bounding box across all available points
        const all = [...(bldPoints || []), ...(parcelPoints || [])];
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        all.forEach(([x, y]) => {
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        });

        const w = maxX - minX || 0.0001;
        const h = maxY - minY || 0.0001;
        const scale = 100 / Math.max(w, h);

        const norm = ([x, y]) => `${(x - minX) * scale},${(maxY - y) * scale}`;

        const parcelSvg = parcelPoints ? `
            <polygon points="${parcelPoints.map(norm).join(' ')}"
                fill="rgba(56,189,248,0.15)" stroke="#38bdf8"
                stroke-width="${w * scale * 0.012}" stroke-linejoin="round">
                <title>Lot boundary · ${parcel.area_sqft || ''} · Intellipins</title>
            </polygon>` : '';

        const buildingSvg = bldPoints ? `
            <polygon points="${bldPoints.map(norm).join(' ')}"
                fill="rgba(34,197,94,0.45)" stroke="#22c55e"
                stroke-width="${w * scale * 0.012}" stroke-linejoin="round">
                <title>Building footprint · OpenStreetMap / Overpass</title>
            </polygon>` : '';

        const scaledW = w * scale;
        const scaledH = h * scale;
        const pad = Math.max(scaledW, scaledH) * 0.1;
        const vbW = scaledW + pad * 2;
        const vbH = scaledH + pad * 2;

        const legend = `
            <div style="font-size:0.6rem;color:var(--text-muted);margin-left:0.75rem;line-height:2;">
                ${buildingSvg  ? `<div><span style="display:inline-block;width:10px;height:10px;background:rgba(34,197,94,0.45);border:1.5px solid #22c55e;margin-right:4px;vertical-align:middle;border-radius:1px;"></span>Building <small>(OSM)</small></div>` : ''}
                ${parcelSvg ? `<div><span style="display:inline-block;width:10px;height:10px;background:rgba(56,189,248,0.15);border:1.5px solid #38bdf8;margin-right:4px;vertical-align:middle;border-radius:1px;"></span>Lot <small>(Intellipins)</small></div>` : ''}
            </div>`;

        return `<div style="display:flex;justify-content:center;align-items:center;padding:1rem;background:rgba(0,0,0,0.1);border-radius:0.5rem;border:1px dashed var(--glass-border);width:max-content;margin:0 auto;">
            <svg viewBox="${-pad} ${-pad} ${vbW} ${vbH}" style="width:160px;height:160px;overflow:visible;">
                ${parcelSvg}
                ${buildingSvg}
            </svg>
            ${legend}
        </div>`;
    }

    const geomStr = renderFootprintSvg(bd.geometry_wkt || null, parcel);

    return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
        <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
            OSM Property Info ${osmTag}
        </h3>
        <div class="metric-grid">
            ${metric('Type', osm.osm_type, src)}
            ${metric('Class', osm.osm_class, src)}
            ${metric('Coords', coords, src)}
            <div class="metric" style="grid-column: span 2;" data-source="${src}">
                <span class="metric-label">Display Name</span>
                <span class="metric-value" style="font-size: 0.8rem;">${osm.display_name}</span>
            </div>
        </div>

        ${Object.keys(bd).length > 0 ? `
        <h4 style="font-size:0.8rem;margin:1.25rem 0 0.5rem;color:var(--text-muted);text-transform:uppercase;border-bottom:1px dashed var(--glass-border);padding-bottom:0.25rem;">Building Details</h4>
        <div class="metric-grid">
            ${metric('Building Use', val(bd.building_type), 'Overpass')}
            ${metric('Levels', val(bd.floors), 'Overpass')}
            ${metric('Units', val(bd.units), 'Overpass')}
            ${metric('Name', val(bd.name), 'Overpass')}
            ${metric('Operator', val(bd.operator), 'Overpass')}
            ${metric('Height', val(bd.height), 'Overpass')}
            ${metric('Building Footprint Area', val(bd.calculated_area), 'Overpass')}
        </div>
        ` : ''}

        ${geomStr !== 'N/A' ? `
        <div class="metric" style="margin-top: 1rem; width: 100%;" data-source="Overpass">
            <span class="metric-label">Building Footprint &amp; Lot Boundary</span>
            <div class="metric-value" style="margin-top: 0.5rem;">
                ${geomStr}
            </div>
        </div>
        ` : ''}
        
        ${Object.keys(osm.amenities_1000m || {}).length > 0 ? `
        <h4 style="font-size:0.8rem;margin:1.25rem 0 0.5rem;color:var(--text-muted);text-transform:uppercase;border-bottom:1px dashed var(--glass-border);padding-bottom:0.25rem;">Amenities (1000m Radius)</h4>
        <div class="metric-grid">
            ${metric('Transit Stops', osm.amenities_1000m.transit || '0', 'Overpass')}
            ${metric('Parks & Leisure', osm.amenities_1000m.parks || '0', 'Overpass')}
            ${metric('Retail & Dining', osm.amenities_1000m.retail || '0', 'Overpass')}
        </div>
        ` : ''}
        
    </div>`;
}

function renderClimate(meteo) {
    const tag = `<span style="font-size:0.65rem;font-weight:400;background:rgba(14,165,233,0.15);color:#0ea5e9;padding:0.1rem 0.4rem;border-radius:999px;margin-left:0.4rem;vertical-align:middle;">Open-Meteo</span>`;
    
    if (meteo?._disabled) {
        return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                Climate Summary (2024) ${tag}
            </h3>
            <div class="metric-grid">
                ${disabledMetric('Precip Days')}${disabledMetric('Rainfall')}
                ${disabledMetric('Snowfall')}${disabledMetric('Hottest Day')}
            </div>
        </div>`;
    }
    
    if (!meteo || Object.keys(meteo).length === 0 || meteo.error) {
        return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                Climate Summary (2024) ${tag}
            </h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">${meteo?.error || 'No data'}</p>
        </div>`;
    }
    
    return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
        <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
            Climate Summary (2024) ${tag}
        </h3>
        <div class="metric-grid">
            ${metric('Precip Days', meteo.annual_precip_days, 'Open-Meteo')}
            ${metric('Rainfall', meteo.annual_precipitation_mm + ' mm', 'Open-Meteo')}
            ${metric('Snowfall', meteo.annual_snowfall_cm + ' cm', 'Open-Meteo')}
            ${metric('Hottest Day', meteo.hottest_day_c + ' °C', 'Open-Meteo')}
            ${metric('Coldest Day', meteo.coldest_day_c + ' °C', 'Open-Meteo')}
        </div>
    </div>`;
}

function renderCrime(crime) {
    const tag = `<span style="font-size:0.65rem;font-weight:400;background:rgba(239,68,68,0.15);color:#ef4444;padding:0.1rem 0.4rem;border-radius:999px;margin-left:0.4rem;vertical-align:middle;">FBI CDE</span>`;
    const src = 'FBI Crime Data Explorer';

    if (crime?._disabled) {
        return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                Crime Data ${tag}
            </h3>
            <div class="metric-grid">
                ${disabledMetric('Violent Crime Rate')}${disabledMetric('vs. National Avg')}${disabledMetric('Crime Score')}
            </div>
        </div>`;
    }

    if (!crime || Object.keys(crime).length === 0 || crime.error) {
        return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                Crime Data ${tag}
            </h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">${crime?.error || 'No data available.'}</p>
        </div>`;
    }

    const vRate      = crime.violent_crime_rate_per_100k;
    const vAvg       = crime.national_avg_violent_per_100k ?? 380;
    const vAbove     = crime.above_national_avg_violent;
    const vDiff      = Math.abs(vRate - vAvg).toFixed(1);

    const vColor     = vAbove ? '#ef4444' : '#4ade80';
    const vVal       = `<span style="color:${vColor}">${vRate}</span> <small style="font-size:0.6rem;color:var(--text-muted)">per 100k</small>`;

    const vDiffColor = vAbove ? '#ef4444' : '#4ade80';
    const vDiffVal   = `<span style="color:${vDiffColor}">${vAbove ? '▲' : '▼'} ${vDiff}</span> <small style="font-size:0.6rem;color:var(--text-muted)">${vAbove ? 'above' : 'below'} avg (${vAvg})</small>`;

    const scoreColor = crime.crime_score > 10 ? '#ef4444' : crime.crime_score > 5 ? '#f59e0b' : '#4ade80';
    const scoreVal   = `<span style="color:${scoreColor}">${crime.crime_score}</span> <small style="font-size:0.6rem;color:var(--text-muted)">/ 15</small>`;

    const pRate  = crime.property_crime_rate_per_100k;
    const pAvg   = crime.national_avg_property_per_100k ?? 2110;
    const pAbove = crime.above_national_avg_property;
    const pDiff  = pRate != null ? Math.abs(pRate - pAvg).toFixed(1) : null;

    const pColor    = pAbove ? '#ef4444' : '#4ade80';
    const pRateVal  = pRate != null
        ? `<span style="color:${pColor}">${pRate}</span> <small style="font-size:0.6rem;color:var(--text-muted)">per 100k</small>`
        : `<span style="color:var(--text-muted)">N/A</span>`;
    const pDiffVal  = pDiff != null
        ? `<span style="color:${pColor}">${pAbove ? '▲' : '▼'} ${pDiff}</span> <small style="font-size:0.6rem;color:var(--text-muted)">${pAbove ? 'above' : 'below'} avg (${pAvg})</small>`
        : `<span style="color:var(--text-muted)">N/A</span>`;

    const vScoreVal = crime.violent_crime_score != null 
        ? `<span style="color:${crime.violent_crime_score > 10 ? '#ef4444' : crime.violent_crime_score > 5 ? '#f59e0b' : '#4ade80'}">${crime.violent_crime_score}</span> <small style="font-size:0.6rem;color:var(--text-muted)">/ 15</small>` 
        : `<span style="color:var(--text-muted)">N/A</span>`;

    const pScoreVal = crime.property_crime_score != null
        ? `<span style="color:${crime.property_crime_score > 10 ? '#ef4444' : crime.property_crime_score > 5 ? '#f59e0b' : '#4ade80'}">${crime.property_crime_score}</span> <small style="font-size:0.6rem;color:var(--text-muted)">/ 15</small>`
        : `<span style="color:var(--text-muted)">N/A</span>`;

    return `<div style="border-top:1px solid var(--glass-border);padding-top:1.5rem;margin-top:1.5rem;">
        <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
            Crime Data ${tag}
        </h3>
        <p style="font-size:0.7rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.04em;margin:0 0 0.4rem;">Violent Crime</p>
        <div class="metric-grid" style="margin-bottom:1rem;">
            ${metric('Violent Crime Rate', vVal,      src)}
            ${metric('vs. National Avg',   vDiffVal,  src)}
            ${metric('Violent Score',      vScoreVal, src)}
        </div>
        <p style="font-size:0.7rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.04em;margin:0 0 0.4rem;">Property Crime</p>
        <div class="metric-grid" style="margin-bottom:1rem;">
            ${metric('Property Crime Rate', pRateVal, src)}
            ${metric('vs. National Avg',    pDiffVal, src)}
            ${metric('Property Score',      pScoreVal, src)}
        </div>
        <p style="font-size:0.7rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.04em;margin:0 0 0.4rem;">Combined</p>
        <div class="metric-grid">
            ${metric('Overall Crime Score', scoreVal, src)}
        </div>
        <p style="font-size:0.7rem;color:var(--text-muted);margin-top:0.75rem;">
            ${crime.city}, ${crime.state} · ${crime.data_year} · ${crime.source}
        </p>
    </div>`;
}

function renderGooglePlaces(g) {
    const googleTag = `<span style="font-size:0.65rem;font-weight:400;background:rgba(66,133,244,0.15);color:#74a8f8;padding:0.1rem 0.4rem;border-radius:999px;margin-left:0.4rem;vertical-align:middle;">Google Places</span>`;

    if (g?._disabled) {
        return `<div style="margin-top:1.5rem;border-top:1px solid var(--glass-border);padding-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                Ratings &amp; Reviews ${googleTag}
            </h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">${DISABLED_VALUE} Google Places API is off.</p>
        </div>`;
    }
    if (!g || g.error) {
        return `<div style="margin-top:1.5rem;border-top:1px solid var(--glass-border);padding-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                Ratings &amp; Reviews ${googleTag}
            </h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">${g?.error || 'No data'}</p>
        </div>`;
    }

    function stars(n) {
        const full  = Math.round(n || 0);
        const color = full >= 4 ? '#10b981' : full >= 3 ? '#f59e0b' : '#ef4444';
        return `<span style="color:${color};letter-spacing:0.05em;">${'★'.repeat(full)}${'☆'.repeat(5 - full)}</span>`;
    }

    const reviewsHtml = (g.reviews || []).map(rv => `
        <div style="padding:0.75rem 0;border-bottom:1px solid var(--glass-border);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem;gap:0.5rem;">
                <span style="font-size:0.78rem;font-weight:600;color:var(--text-main);">${rv.author}</span>
                <div style="display:flex;align-items:center;gap:0.5rem;flex-shrink:0;">
                    <span style="font-size:0.8rem;">${stars(rv.rating)}</span>
                    ${rv.time ? `<span style="font-size:0.65rem;color:#818cf8;white-space:nowrap;">${rv.time}</span>` : ''}
                </div>
            </div>
            ${rv.text ? `<p style="font-size:0.75rem;color:var(--text-muted);line-height:1.55;margin:0;">${rv.text}</p>` : ''}
        </div>`).join('');

    return `<div style="margin-top:1.5rem;border-top:1px solid var(--glass-border);padding-top:1.5rem;">
        <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
            Ratings &amp; Reviews ${googleTag}
        </h3>
        <div style="display:flex;align-items:center;gap:1.25rem;margin-bottom:1rem;padding:0.75rem 1rem;background:rgba(66,133,244,0.05);border-radius:0.75rem;border:1px solid rgba(66,133,244,0.15);">
            <div style="text-align:center;">
                <span style="font-size:2rem;font-weight:800;color:#74a8f8;">${g.rating ?? 'N/A'}</span>
                <span style="font-size:0.65rem;color:var(--text-muted);display:block;margin-top:0.1rem;">/ 5</span>
            </div>
            <div>
                <div style="font-size:1.1rem;margin-bottom:0.2rem;">${stars(g.rating)}</div>
                <div style="font-size:0.72rem;color:var(--text-muted);">${g.review_count != null ? `${g.review_count.toLocaleString()} reviews` : 'No reviews'} · ${g.place_name}</div>
                ${g.matched_via ? `<div style="font-size:0.62rem;color:#475569;margin-top:0.2rem;">matched via ${g.matched_via === 'address' ? 'property address' : 'company name'}</div>` : ''}
            </div>
        </div>
        ${reviewsHtml || '<p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;">No written reviews available.</p>'}
    </div>`;
}

function safeHref(url) {
    if (!url) return '#';
    return url.replace(/&/g, '&amp;').replace(/"/g, '%22');
}

function renderNews(news) {
    if (news?._disabled) {
        return `<p style="font-size:0.8rem;font-style:italic;color:var(--text-muted);">${DISABLED_VALUE} NewsAPI is off.</p>`;
    }

    const items = news?.latest_news;
    if (!items) return `<p style="color:var(--text-muted);font-size:0.8rem;">No news data.</p>`;

    if (!Array.isArray(items) || items.length === 0) {
        return `<p style="color:var(--text-muted);font-size:0.8rem;">${typeof items === 'string' ? items : 'No recent news found.'}</p>`;
    }

    return items.map(({ title, snippet, date, url, source, city_match }) => {
        console.log('[News] url:', url, '| source:', source);
        return `
        <div style="padding:0.75rem 0;border-bottom:1px solid var(--glass-border);">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.75rem;margin-bottom:0.3rem;">
                <a href="${safeHref(url)}" target="_blank" rel="noopener noreferrer"
                   style="font-size:0.82rem;font-weight:600;color:var(--text-main);line-height:1.4;flex:1;text-decoration:none;">
                    ${title}
                </a>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.25rem;flex-shrink:0;">
                    ${date ? `<span style="font-size:0.68rem;color:#818cf8;white-space:nowrap;font-weight:600;">${date}</span>` : ''}
                    ${city_match ? `<span style="font-size:0.6rem;background:rgba(16,185,129,0.1);color:#10b981;padding:0.1rem 0.4rem;border-radius:999px;white-space:nowrap;">local</span>` : ''}
                </div>
            </div>
            ${snippet ? `<p style="font-size:0.75rem;color:var(--text-muted);line-height:1.5;margin:0;">${snippet}</p>` : ''}
            ${source ? `<p style="font-size:0.68rem;color:#475569;margin:0.3rem 0 0;">via ${source}</p>` : ''}
        </div>`;
    }).join('');
}

// ── Main display ────────────────────────────────────────────────────────────
function displayResults(data) {
    const { enrichment } = data;
    const census    = enrichment.census;
    const geocoords = enrichment.geocoords || {};

    const geoSourceMap = {
        intellipins: 'Intellipins',
        nominatim:   'OSM Nominatim',
        census:      'US Census Geocoder',
        none:        'unavailable',
    };
    const geoLabel = geoSourceMap[geocoords.source] || geocoords.source || 'unknown';
    const geoNote  = geocoords.lat != null
        ? `<div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.5rem;text-align:right;">
               Geocoded via <strong style="color:#fbbf24;">${geoLabel}</strong>
               &nbsp;&middot;&nbsp;${parseFloat(geocoords.lat).toFixed(5)}, ${parseFloat(geocoords.lon).toFixed(5)}
           </div>`
        : '';

    resultsContent.innerHTML = `
        <div class="status-badge" style="background:rgba(99,102,241,0.1);color:#818cf8;margin-top:1rem;">
            Market Context: ${data.lead_info.city}, ${data.lead_info.state}
        </div>
        ${geoNote}

        ${renderWikiSection(enrichment.wikipedia)}
        ${renderIntelliPins(enrichment.intellipins)}
        ${renderOSM(enrichment.osm, enrichment.intellipins?.parcel)}
        ${renderClimate(enrichment.open_meteo)}
        ${renderCrime(enrichment.crime)}
        ${renderCensusMetrics(enrichment.census)}
        ${renderFredMetrics(enrichment.fred)}
        ${renderWalkScore(enrichment.walkscore)}

        ${renderGooglePlaces(enrichment.google)}

        <div style="margin-top:1.5rem;border-top:1px solid var(--glass-border);padding-top:1.5rem;">
            <h3 style="font-size:0.9rem;margin-bottom:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">
                Company News
                <span style="font-size:0.65rem;font-weight:400;background:rgba(99,102,241,0.15);color:#818cf8;padding:0.1rem 0.4rem;border-radius:999px;margin-left:0.4rem;">NewsAPI</span>
            </h3>
            ${renderNews(enrichment.news)}
        </div>

        <div style="margin-top:1.5rem;padding:1rem;background:rgba(16,185,129,0.05);border-radius:1rem;border:1px dashed var(--accent);">
            <h3 style="font-size:0.875rem;color:var(--accent);margin-bottom:0.5rem;">GTM Insight</h3>
            <p style="font-size:0.75rem;color:var(--text-muted);">
                ${data.lead_info.company} is located in ${data.lead_info.city}.
                ${census && !census._disabled && census.renter_percentage
                    ? `A renter percentage of ${census.renter_percentage} indicates a strong fit for EliseAI's multifamily solutions.`
                    : 'Further verification needed for market density.'}
            </p>
        </div>
    `;
}

// ── Pipeline: score dashboard ────────────────────────────────────────────────
function scoreColor(s) {
    if (typeof s !== 'number') return 'var(--text-muted)';
    return s >= 70 ? '#10b981' : s >= 50 ? '#f59e0b' : '#ef4444';
}

function renderScoreDashboard(scores) {
    if (!scores) return '';

    const ls = scores.lead_score || {};
    const leadScore = ls.score ?? null;
    const leadGrade = ls.grade ?? '—';
    const leadColor = scoreColor(leadScore);

    const subCards = ['demand', 'friction', 'scale', 'opportunity'].map(key => {
        const s  = scores[key] || {};
        const sc = s.score ?? null;
        const color = scoreColor(sc);
        const pct   = typeof sc === 'number' ? sc : 0;
        const label = key.charAt(0).toUpperCase() + key.slice(1);
        const caveat = (s.available_weight || 0) < 0.50
            ? `<span class="score-caveat">partial data</span>` : '';
        return `
        <div class="score-card">
            <span class="score-label">${label}</span>
            <span class="score-value" style="color:${color}">${typeof sc === 'number' ? sc.toFixed(1) : '—'}</span>
            <div class="score-bar"><div class="score-fill" style="width:${pct}%;background:${color};"></div></div>
            ${caveat}
        </div>`;
    }).join('');

    const newsSentiment = scores.opportunity?.news_sentiment || 'none';
    const newsColors = { growth: '#10b981', cost_pressure: '#f59e0b', trouble: '#ef4444', mixed: '#f59e0b', neutral: '#94a3b8', none: '#475569' };
    const newsLabel  = { growth: '↑ Growth', cost_pressure: '⚠ Cost Pressure', trouble: '⚠ Trouble', mixed: '~ Mixed', neutral: '– Neutral', none: '– No News' };
    const nColor = newsColors[newsSentiment] || '#94a3b8';
    const nLabel = newsLabel[newsSentiment]  || newsSentiment;

    return `
    <div class="pipeline-section">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:0.75rem;">
            <div>
                <h3 class="section-heading" style="margin-bottom:0.25rem;">GTM Score Analysis</h3>
                <span style="font-size:0.68rem;color:${nColor};background:${nColor}1a;padding:0.15rem 0.5rem;border-radius:999px;font-weight:600;">News: ${nLabel}</span>
            </div>
            <div class="lead-score-bubble" style="color:${leadColor};border-color:${leadColor};">
                <span class="lead-score-grade">${leadGrade}</span>
                <span class="lead-score-number">${typeof leadScore === 'number' ? leadScore.toFixed(1) : '—'}</span>
                <span class="lead-score-label">Lead Score</span>
            </div>
        </div>
        <div class="score-grid">${subCards}</div>
    </div>`;
}

// ── Pipeline: pain points ────────────────────────────────────────────────────
function renderPainPoints(painPoints) {
    if (!Array.isArray(painPoints) || painPoints.length === 0) {
        return `<div class="pipeline-section">
            <h3 class="section-heading">Pain Points</h3>
            <p style="font-size:0.8rem;color:var(--text-muted);font-style:italic;margin-top:0.5rem;">No pain points detected.</p>
        </div>`;
    }
    const sevColor = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' };
    const items = painPoints.map(pp => {
        const color = sevColor[pp.severity] || '#94a3b8';
        const srcBadge = pp.source === 'llm'
            ? `<span style="font-size:0.55rem;background:rgba(99,102,241,0.15);color:#818cf8;padding:0.1rem 0.35rem;border-radius:999px;font-weight:700;">AI</span>`
            : `<span style="font-size:0.55rem;background:rgba(16,185,129,0.1);color:#10b981;padding:0.1rem 0.35rem;border-radius:999px;font-weight:700;">rule</span>`;
        return `
        <div class="pain-point-card">
            <div style="display:flex;align-items:center;gap:0.45rem;margin-bottom:0.3rem;flex-wrap:wrap;">
                <span style="width:7px;height:7px;background:${color};border-radius:50%;flex-shrink:0;display:inline-block;"></span>
                <span style="font-size:0.82rem;font-weight:700;color:var(--text-main);">${pp.label}</span>
                <span style="font-size:0.6rem;font-weight:700;color:${color};background:${color}1a;padding:0.1rem 0.4rem;border-radius:999px;text-transform:uppercase;">${pp.severity}</span>
                ${srcBadge}
            </div>
            <p style="font-size:0.75rem;color:var(--text-muted);line-height:1.55;margin:0 0 0 1.2rem;">${pp.description}</p>
        </div>`;
    }).join('');
    return `<div class="pipeline-section">
        <h3 class="section-heading">Pain Points Detected <small style="font-size:0.65rem;font-weight:400;color:var(--text-muted);">(${painPoints.length})</small></h3>
        <div style="display:flex;flex-direction:column;gap:0.65rem;margin-top:0.75rem;">${items}</div>
    </div>`;
}

// ── Pipeline: outreach email ─────────────────────────────────────────────────
function renderOutreach(outreach) {
    if (!outreach) return '';
    if (outreach.error && !outreach.message) {
        return `<div class="pipeline-section">
            <h3 class="section-heading">Personalized Outreach Email</h3>
            <p style="font-size:0.8rem;color:#ef4444;margin-top:0.5rem;">${outreach.error}</p>
        </div>`;
    }
    const subject = outreach.subject || '';
    const msgHtml = (outreach.message || '').replace(/\n/g, '<br>');
    return `
    <div class="pipeline-section">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;gap:0.5rem;flex-wrap:wrap;">
            <h3 class="section-heading" style="margin:0;">Personalized Outreach Email</h3>
            <button id="copy-outreach-btn" onclick="copyOutreach()" style="width:auto;margin:0;padding:0.3rem 0.85rem;font-size:0.7rem;background:rgba(16,185,129,0.08);color:#10b981;border:1px solid rgba(16,185,129,0.3);border-radius:999px;font-weight:700;">Copy</button>
        </div>
        <div id="outreach-content" style="background:rgba(0,0,0,0.15);border-radius:0.75rem;border:1px solid var(--glass-border);overflow:hidden;">
            <div style="padding:0.65rem 1rem;background:rgba(16,185,129,0.04);border-bottom:1px solid var(--glass-border);">
                <span style="font-size:0.62rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;font-weight:700;">Subject</span>
                <p style="font-size:0.85rem;color:var(--text-main);margin-top:0.2rem;font-weight:600;line-height:1.4;">${subject}</p>
            </div>
            <div style="padding:1rem 1.1rem;font-size:0.82rem;line-height:1.75;color:var(--text-main);">${msgHtml}</div>
        </div>
        ${outreach.generated_at ? `<p style="font-size:0.62rem;color:var(--text-muted);margin-top:0.4rem;text-align:right;">Generated ${new Date(outreach.generated_at).toLocaleString()}</p>` : ''}
    </div>`;
}

window.copyOutreach = function () {
    const el = document.getElementById('outreach-content');
    if (!el) return;
    // Build plain-text copy (subject + message)
    const lines = [];
    const subjEl = el.querySelector('p');
    if (subjEl) lines.push('Subject: ' + subjEl.innerText, '');
    const bodyEl = el.querySelector('div:last-child');
    if (bodyEl) lines.push(bodyEl.innerText);
    navigator.clipboard.writeText(lines.join('\n')).then(() => {
        const btn = document.getElementById('copy-outreach-btn');
        if (btn) { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = 'Copy'; }, 2000); }
    });
};

// ── Pipeline: full display ───────────────────────────────────────────────────
function displayPipelineResults(data) {
    displayResults(data);   // render enrichment sections first

    const pipelineHtml = `
        <div class="pipeline-header">
            <span class="status-badge" style="background:rgba(99,102,241,0.1);color:#818cf8;">
                Full Pipeline — ${data.lead_info.company}, ${data.lead_info.city}, ${data.lead_info.state}
            </span>
            ${data.id ? `<p style="font-size:0.62rem;color:var(--text-muted);margin-top:0.25rem;">Lead ID: ${data.id}</p>` : ''}
        </div>
        ${renderScoreDashboard(data.scores)}
        ${renderPainPoints(data.pain_points)}
        ${renderOutreach(data.outreach)}
        <div style="border-top:2px dashed var(--glass-border);padding-top:1.25rem;margin-top:0.5rem;">
            <h3 style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem;">Raw Enrichment Data</h3>
        </div>
    `;
    resultsContent.innerHTML = pipelineHtml + resultsContent.innerHTML;
}

// ── Pipeline button handler ──────────────────────────────────────────────────
const pipelineBtn = document.getElementById('pipeline-btn');

pipelineBtn.addEventListener('click', async () => {
    const formData = {
        id:               currentTestProfileId,
        name:             document.getElementById('name').value,
        company:          document.getElementById('company').value,
        property_address: document.getElementById('property_address').value,
        city:             document.getElementById('city').value,
        state:            document.getElementById('state').value,
        email:            document.getElementById('email').value,
        enabled_apis:     enabledApis(),
        llm_provider:     llmProvider,
    };

    // Basic validation
    if (!formData.name || !formData.company || !formData.property_address || !formData.city || !formData.state) {
        alert('Please fill in all required fields before running the pipeline.');
        return;
    }

    resultsCard.classList.add('visible');
    loadingIndicator.style.display = 'block';
    loadingIndicator.querySelector('p').textContent = 'Running full pipeline (enrich → score → pain points → outreach)…';
    resultsContent.innerHTML = '';
    submitBtn.disabled = true;
    pipelineBtn.disabled = true;
    pipelineBtn.textContent = 'Running Pipeline…';

    try {
        const response = await fetch('http://localhost:8000/pipeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Pipeline failed' }));
            throw new Error(err.detail || 'Pipeline failed');
        }
        displayPipelineResults(await response.json());
    } catch (error) {
        resultsContent.innerHTML = `<p style="color:#ef4444;">Pipeline error: ${error.message}. Make sure the backend is running.</p>`;
    } finally {
        loadingIndicator.style.display = 'none';
        loadingIndicator.querySelector('p').textContent = 'Enriching data from APIs…';
        submitBtn.disabled = false;
        pipelineBtn.disabled = false;
        pipelineBtn.textContent = 'Run Full Pipeline';
    }
});
