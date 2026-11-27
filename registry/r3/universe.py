"""Ghostlyne R3 discovery universe: the AI-infrastructure stack and its distant economy.
Admission rationales are reasons to look, not causal findings."""
F = lambda seg, name: dict(segment=seg, name=name)
FOCAL = {  # D0, financial instruments (share prices are not product prices)
 "NVDA": F("Compute", "Nvidia"), "AMD": F("Compute", "AMD"), "AVGO": F("Compute", "Broadcom"), "TSM": F("Compute", "TSMC (ADR)"), "MRVL": F("Compute", "Marvell"),
 "MU": F("Memory", "Micron"), "000660.KS": F("Memory", "SK hynix"), "005930.KS": F("Memory", "Samsung Electronics"),
 "ANET": F("Networking & optics", "Arista"), "COHR": F("Networking & optics", "Coherent"), "LITE": F("Networking & optics", "Lumentum"), "CIEN": F("Networking & optics", "Ciena"),
 "SMCI": F("Servers & assembly", "Supermicro"), "2382.TW": F("Servers & assembly", "Quanta"), "2317.TW": F("Servers & assembly", "Hon Hai (Foxconn)"), "3231.TW": F("Servers & assembly", "Wistron"),
 "ETN": F("Power & cooling", "Eaton"), "2308.TW": F("Power & cooling", "Delta Electronics"), "SU.PA": F("Power & cooling", "Schneider Electric"),
 "EQIX": F("Data centres", "Equinix"), "DLR": F("Data centres", "Digital Realty"),
 "AMAT": F("Equipment & packaging", "Applied Materials"), "LRCX": F("Equipment & packaging", "Lam Research"), "ASML": F("Equipment & packaging", "ASML"),
 "8035.T": F("Equipment & packaging", "Tokyo Electron"), "4062.T": F("Equipment & packaging", "Ibiden (substrates)"),
}
REVENUE = {  # D0 fundamentals: monthly revenue from Taiwan Stock Exchange mandatory disclosures
 "REV_2330": F("Compute", "TSMC revenue"), "REV_2382": F("Servers & assembly", "Quanta revenue"), "REV_2317": F("Servers & assembly", "Hon Hai revenue"),
 "REV_3231": F("Servers & assembly", "Wistron revenue"), "REV_6669": F("Servers & assembly", "Wiwynn revenue"), "REV_2308": F("Power & cooling", "Delta Electronics revenue"),
 "REV_2345": F("Networking & optics", "Accton revenue"), "REV_3037": F("Equipment & packaging", "Unimicron revenue"), "REV_3711": F("Equipment & packaging", "ASE revenue"),
 "REV_2408": F("Memory", "Nanya revenue"),
}
E = lambda ring, name, why, role="candidate", tr="dlog": dict(ring=ring, name=name, why=why, role=role, transform=tr)
EXTERNALS = {
 # D2 industrial and material dependencies
 "HG=F": E(2, "Copper", "power distribution, cabling and cooling in data centres"),
 "ALI=F": E(2, "Aluminum", "server chassis, heat sinks, busbars"),
 "SI=F": E(2, "Silver", "contacts and conductive pastes"),
 "PA=F": E(2, "Palladium", "plating and capacitors"),
 "LIN": E(2, "Linde (industrial gases)", "helium, neon and process gases for fabs"),
 "REMX": E(2, "Rare earths and strategic metals", "magnets, motors and specialty metals"),
 "ALB": E(2, "Albemarle (lithium)", "backup batteries; competing battery demand"),
 # D3 indirect: energy, mining, logistics
 "BZ=F": E(3, "Brent crude (Middle East benchmark)", "energy and transport costs across the chain"),
 "CL=F": E(3, "WTI crude", "US energy and transport costs"),
 "NG=F": E(3, "Natural gas", "power generation cost for data centres"),
 "URA": E(3, "Uranium", "nuclear power contracted for data-centre load"),
 "XLU": E(3, "US utilities", "electricity supply to data centres"),
 "BHP": E(3, "BHP", "diversified mining"),
 "FCX": E(3, "Freeport-McMoRan", "copper mining (Americas, Indonesia)"),
 "IVN.TO": E(3, "Ivanhoe Mines (DR Congo copper)", "African copper supply"),
 "FM.TO": E(3, "First Quantum (Zambia copper)", "African copper supply"),
 "1919.HK": E(3, "COSCO Shipping", "Asian container logistics"),
 "MAERSK-B.CO": E(3, "Maersk", "global container shipping"),
 "2603.TW": E(3, "Evergreen Marine", "Taiwan container shipping for electronics"),
 "2609.TW": E(3, "Yang Ming Marine", "Taiwan container shipping"),
 "1308.HK": E(3, "SITC International", "intra-Asia container shipping"),
 "FDX": E(3, "FedEx (air cargo)", "chips and servers move by air"),
 "CAT": E(3, "Caterpillar", "construction and generators, including data centres"),
 # D4 remote: currencies, weather
 "KRW=X": E(4, "Korean won", "currency of memory makers"),
 "TWD=X": E(4, "Taiwan dollar", "currency of foundry, packaging and server assembly"),
 "JPY=X": E(4, "Japanese yen", "currency of equipment and materials suppliers"),
 "CNY=X": E(4, "Chinese yuan", "currency of electronics assembly and demand"),
 "NINO34_W": E(4, "El Niño sea temperature", "Taiwan and Korea rainfall, fab water", tr="diff"),
 # D5 distant: competing demand
 "BTC-USD": E(5, "Bitcoin", "competes for GPUs and electricity"),
 "ZC=F": E(5, "Corn", "competes for water and power; ethanol"),
 "TM": E(5, "Toyota", "competing chip demand from carmakers"),
 # negative controls
 "OJ=F": E(0, "Orange juice", "negative control", "negative_control"),
 "HE=F": E(0, "Lean hogs", "negative control", "negative_control"),
 "LE=F": E(0, "Live cattle", "negative control", "negative_control"),
 "SYN_1": E(0, "Synthetic 1", "synthetic control", "synthetic_control"),
 "SYN_2": E(0, "Synthetic 2", "synthetic control", "synthetic_control"),
 "SYN_3": E(0, "Synthetic 3", "synthetic control", "synthetic_control"),
}
CHAINS = [  # pre-specified multi-hop paths: distant -> intermediate -> AI infrastructure (monthly)
 ("BZ=F", "MAERSK-B.CO", "2382.TW"), ("BZ=F", "1919.HK", "2317.TW"), ("BZ=F", "2603.TW", "3231.TW"),
 ("HG=F", "IVN.TO", "ETN"), ("HG=F", "FM.TO", "SU.PA"), ("HG=F", "ETN", "EQIX"),
 ("NG=F", "XLU", "DLR"), ("URA", "XLU", "NVDA"), ("KRW=X", "000660.KS", "NVDA"),
 ("NINO34_W", "TWD=X", "TSM"), ("BTC-USD", "AMD", "MU"), ("ALI=F", "2308.TW", "SMCI"),
]
UNAVAILABLE = {
 "DRAM, NAND and HBM prices": "DRAMeXchange licence required (founder decision)",
 "GPU prices and GPU rental rates": "no free historical series with usable coverage",
 "Data-centre construction and power-queue data": "no weekly or monthly free series integrated yet",
 "Baltic Dry and container freight indices": "licensed (Baltic Exchange, Drewry, Freightos); shipping equities used instead",
 "Saudi Aramco and Gulf logistics equities": "listed 2019 or later; too short for exploration",
 "Vertiv, GE Vernova, Credo": "listed too recently for the exploration window",
}
