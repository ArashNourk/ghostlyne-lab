"""Ghostlyne R2 discovery universe: semiconductor memory. Each variable carries its economic admission rationale.
An admission rationale is a reason to look, not a causal finding."""
FOCAL = {  # weekly track: financial instruments, NOT memory prices
 "MU":        dict(name="Micron (share price)", note="US memory maker: DRAM, HBM, NAND"),
 "000660.KS": dict(name="SK hynix (share price)", note="DRAM and HBM leader"),
 "005930.KS": dict(name="Samsung Electronics (share price)", note="largest memory maker; also phones, displays, foundry"),
 "2408.TW":   dict(name="Nanya Technology (share price)", note="DRAM pure-play"),
 "2344.TW":   dict(name="Winbond (share price)", note="specialty DRAM and NOR flash"),
 "3260.TWO":  dict(name="ADATA (share price)", note="memory module maker; margins move with DRAM and NAND spot prices"),
 "4967.TW":   dict(name="TeamGroup (share price)", note="memory module maker"),
}
FOCAL_MONTHLY = {  # monthly track: actual memory-market activity from regulatory filings
 "NANYA_REV":   dict(name="Nanya monthly revenue", code="2408", note="DRAM pure-play sales, TWSE monthly disclosure"),
 "WINBOND_REV": dict(name="Winbond monthly revenue", code="2344", note="specialty DRAM and flash sales, TWSE monthly disclosure"),
}
MARKET = "ACWI"  # global equity factor removed for 'adjusted' association
E = lambda ring, name, why, role="candidate", transform="dlog": dict(ring=ring, name=name, why=why, role=role, transform=transform)
EXTERNALS = {
 # D1 direct dependencies
 "AMAT":    E(1, "Applied Materials", "deposition and etch tools for memory fabs"),
 "8035.T":  E(1, "Tokyo Electron", "etch, deposition and coater tools; large memory-fab exposure"),
 "ASML":    E(1, "ASML", "lithography, including EUV for leading DRAM nodes"),
 "ETN":     E(1, "Eaton", "power equipment for data centres that buy server memory"),
 "ABBN.SW": E(1, "ABB", "switchgear and transformers for data centres and fabs"),
 # D2 industrial and material dependencies
 "HG=F":    E(2, "Copper futures", "interconnect, wiring and cooling in fabs and data centres"),
 "SI=F":    E(2, "Silver futures", "conductive pastes and contacts in electronics"),
 "ALI=F":   E(2, "Aluminum futures", "enclosures and heat sinks; fab construction"),
 "PA=F":    E(2, "Palladium futures", "plating and capacitors; Russia supply shared with neon"),
 "LIN":     E(2, "Linde", "industrial and electronic gases including neon and helium"),
 "APD":     E(2, "Air Products", "electronic gases and helium supply to fabs"),
 "4063.T":  E(2, "Shin-Etsu Chemical", "silicon wafers and photoresists"),
 "3436.T":  E(2, "SUMCO", "silicon wafers; memory makers are major buyers"),
 "ENTG":    E(2, "Entegris", "specialty chemicals and filtration for fabs"),
 "REMX":    E(2, "Rare earth and strategic metals ETF", "rare earths and strategic metals in electronics supply chains"),
 # D3 indirect industrial and economic dependencies
 "CL=F":    E(3, "Crude oil futures", "energy and transport costs across the supply chain"),
 "NG=F":    E(3, "Natural gas futures", "power cost for fabs and data centres"),
 "URA":     E(3, "Uranium ETF", "nuclear power contracted for data-centre load"),
 "XLU":     E(3, "US utilities", "electricity supply to data centres"),
 "1919.HK": E(3, "COSCO Shipping Holdings", "Chinese container logistics carrying electronics"),
 "MAERSK-B.CO": E(3, "Maersk", "global container shipping"),
 "2603.TW": E(3, "Evergreen Marine", "Taiwan container shipping carrying electronics"),
 "FDX":     E(3, "FedEx", "air cargo; chips and modules move by air"),
 "UNP":     E(3, "Union Pacific", "US rail freight and industrial activity"),
 "BHP":     E(3, "BHP", "mining of copper and other inputs"),
 "FCX":     E(3, "Freeport-McMoRan", "copper mining"),
 "CAT":     E(3, "Caterpillar", "industrial machinery and construction, including data centres"),
 # D4 remote dependencies
 "KRW=X":   E(4, "Korean won per US dollar", "currency of the two largest memory makers"),
 "TWD=X":   E(4, "Taiwan dollar per US dollar", "currency of Nanya, Winbond and module makers"),
 "JPY=X":   E(4, "Japanese yen per US dollar", "currency of equipment and materials suppliers"),
 "CNY=X":   E(4, "Chinese yuan per US dollar", "currency of the largest electronics assembler and new memory entrants"),
 "NINO34_W": E(4, "El Niño sea-surface temperature", "drives Taiwan and Korea rainfall, which fabs depend on for water", transform="diff"),
 # D5 distant but defensible dependencies
 "BTC-USD": E(5, "Bitcoin", "crypto mining competes for GPUs, memory and electricity"),
 "ZC=F":    E(5, "Corn futures", "farming and ethanol compete for water and power"),
 "TM":      E(5, "Toyota", "car makers compete for chip supply"),
 "ALB":     E(5, "Albemarle (lithium)", "battery demand competes for materials, power and capital"),
 # negative controls: no admitted pathway
 "OJ=F":    E(0, "Orange juice futures", "negative control", role="negative_control"),
 "HE=F":    E(0, "Lean hog futures", "negative control", role="negative_control"),
 "LE=F":    E(0, "Live cattle futures", "negative control", role="negative_control"),
 "SYN_1":   E(0, "Synthetic random walk 1", "synthetic negative control", role="synthetic_control"),
 "SYN_2":   E(0, "Synthetic random walk 2", "synthetic negative control", role="synthetic_control"),
 "SYN_3":   E(0, "Synthetic random walk 3", "synthetic negative control", role="synthetic_control"),
}
UNAVAILABLE = {
 "DDR4/DDR5/DRAM/NAND spot and contract prices": "DRAMeXchange (TrendForce) membership required; public pages show current snapshots only; not collected without a licence and founder approval",
 "HBM prices": "no public price series exists; contract terms are private",
 "GPU and accelerator prices, GPU rental rates": "no free historical series with usable coverage found",
 "Korea semiconductor exports (10-day)": "requires a Korean public-data API key",
 "Taiwan reservoir levels": "Water Resources Agency open data not reachable without a dedicated integration; deferred",
 "NY Fed supply-chain pressure index": "download failed in R1 and R2 probes",
 "FRED daily FX and energy": "timed out in the R2 probe; replaced by Yahoo FX and futures series",
}
