"""Ghostlyne R4 universe: North American wholesale power and natural gas (initial focus ERCOT North and Henry Hub).
Rings measure economic distance from the focal energy market. Admission rationales are reasons to look, not causal claims."""
F = lambda name, kind, use: dict(name=name, kind=kind, use=use)
FOCAL = {
 "ERCOT_N_DA":   F("ERCOT North hub, day-ahead price", "power", "short-term"),
 "ERCOT_N_RT":   F("ERCOT North hub, real-time price", "power", "short-term"),
 "ERCOT_N_DART": F("ERCOT North day-ahead minus real-time spread", "spread", "short-term"),
 "ERCOT_WN_BASIS": F("ERCOT West minus North day-ahead basis", "spread", "short-term"),
 "ERCOT_N_HEAT": F("ERCOT North implied heat rate (day-ahead / Henry Hub)", "ratio", "short-term"),
 "HH_SPOT":      F("Henry Hub natural gas spot price", "gas", "short-term"),
 "NG_FRONT":     F("NYMEX natural gas front-month futures", "gas", "procurement"),
}
X = lambda ring, name, why, role="candidate", freq="d", tr="dlog": dict(ring=ring, name=name, why=why, role=role, freq=freq, tr=tr)
EXTERNALS = {
 # D1 direct physical drivers (several double as empirical positive controls)
 "HH_SPOT":   X(1, "Henry Hub spot", "gas sets the marginal cost of most Texas power"),
 "DD_DFW":    X(1, "Dallas temperature stress (degree days)", "heating and cooling demand in the North zone", tr="diff"),
 "DD_IAH":    X(1, "Houston temperature stress (degree days)", "cooling demand in the Houston zone", tr="diff"),
 "LOAD_ERCO": X(1, "ERCOT demand", "demand clears against the supply stack"),
 "LOADFC_ERCO": X(1, "ERCOT day-ahead demand forecast", "the expectation the day-ahead market prices"),
 "WIND_ERCO": X(1, "ERCOT wind generation", "zero-cost supply pushes prices down"),
 "SOLAR_ERCO": X(1, "ERCOT solar generation", "midday supply and evening ramps"),
 "GASGEN_ERCO": X(1, "ERCOT gas-fired generation", "gas plants on the margin"),
 "NUC_ERCO":  X(1, "ERCOT nuclear output", "outages remove baseload supply"),
 "STORAGE_SURPRISE": X(1, "US gas storage change vs seasonal norm", "storage builds signal gas balance", freq="w", tr="level"),
 # D2 wider energy complex
 "CL=F":  X(2, "WTI crude", "oil-linked gas and fuel substitution"),
 "BZ=F":  X(2, "Brent crude", "global energy price level"),
 "TTF=F": X(2, "European gas (TTF)", "pulls US LNG exports and Henry Hub"),
 "LNG":   X(2, "Cheniere (US LNG exporter)", "LNG export economics"),
 "LOAD_PJM": X(2, "PJM demand", "eastern gas burn competes for the same gas"),
 "LOAD_MISO": X(2, "MISO demand", "neighbouring demand and gas burn"),
 "LOAD_SWPP": X(2, "SPP demand", "neighbouring demand"),
 "WIND_SWPP": X(2, "SPP wind generation", "regional wind regime shared with West Texas"),
 "DD_PHL": X(2, "Philadelphia temperature stress", "eastern heating demand for gas", tr="diff"),
 "DD_BOS": X(2, "Boston temperature stress", "New England winter gas demand", tr="diff"),
 # D3 industrial, financial, logistics
 "HG=F":  X(3, "Copper", "industrial activity and electrification demand"),
 "CAD=X": X(3, "Canadian dollar per US dollar", "Canada is the largest gas trading partner"),
 "MXN=X": X(3, "Mexican peso per US dollar", "Texas pipeline exports to Mexico"),
 "XLU":   X(3, "US utilities", "utility equity view of power demand"),
 "VST":   X(3, "Vistra (Texas generator)", "equity view of Texas power margins"),
 "BDRY":  X(3, "Dry bulk shipping", "global industrial freight"),
 # D4 remote: climate, agriculture
 "NINO34": X(4, "El Niño sea temperature", "seasonal weather regimes over Texas", freq="w", tr="diff"),
 "ZC=F":  X(4, "Corn", "agricultural load, ethanol and water"),
 # D5 distant: AI infrastructure and crypto mining
 "BTC-USD": X(5, "Bitcoin", "Texas miners curtail when power is expensive"),
 "MARA":  X(5, "MARA Holdings (bitcoin miner)", "miner economics and Texas load"),
 "RIOT":  X(5, "Riot Platforms (Texas miner)", "large flexible load in ERCOT"),
 "NVDA":  X(5, "Nvidia", "AI build-out driving data-centre load"),
 "SOXX":  X(5, "Semiconductor index", "chip cycle and data-centre build-out"),
 "DLR":   X(5, "Digital Realty", "data-centre operator"),
 "EQIX":  X(5, "Equinix", "data-centre operator"),
 # comparison benchmarks (distant real series; not assumed to be true negatives) and synthetic negatives
 "OJ=F":  X(0, "Orange juice", "comparison benchmark", role="benchmark"),
 "HE=F":  X(0, "Lean hogs", "comparison benchmark", role="benchmark"),
 "SYN_1": X(0, "Synthetic 1", "synthetic negative control", role="synthetic"),
 "SYN_2": X(0, "Synthetic 2", "synthetic negative control", role="synthetic"),
 "SYN_3": X(0, "Synthetic 3", "synthetic negative control", role="synthetic"),
}
POSITIVE_CONTROLS = [  # (focal-side series, driver, family, expected sign): known energy relationships the lab must recover
 ("ERCOT_N_DA", "HH_SPOT", "A_d", +1), ("ERCOT_N_DA", "DD_DFW", "A_d", +1), ("LOAD_ERCO", "DD_DFW", "A_d", +1),
 ("ERCOT_N_DA", "LOAD_ERCO", "A_d", +1), ("ERCOT_N_DA", "WIND_ERCO", "A_d", -1), ("HH_SPOT", "STORAGE_SURPRISE", "A_w", -1),
]
YAHOO = ["NG=F", "CL=F", "BZ=F", "TTF=F", "LNG", "HG=F", "CAD=X", "MXN=X", "XLU", "VST", "BDRY", "ZC=F", "BTC-USD", "MARA", "RIOT", "NVDA", "SOXX", "DLR", "EQIX", "OJ=F", "HE=F"]
UNAVAILABLE = {
 "PJM West and other PJM hubs": "PJM Data Miner requires an API key registered by the company (free); not yet registered",
 "Mass Hub (ISO-NE)": "daily files are public; terms of use not yet confirmed, deferred to R5",
 "Regional gas hubs (Waha, Houston Ship Channel, etc.)": "licensed from price reporters (NGI, Platts); not purchased",
 "Historical weather forecasts": "not obtained; predictive tests use only lagged observations and ERCOT's published day-ahead demand forecast",
 "Power forwards": "exchange and broker data are licensed",
 "Data-centre load and interconnection queues": "no consistent public daily series; AI build-out enters through equity proxies",
}
