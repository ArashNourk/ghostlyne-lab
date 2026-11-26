"""Ghostlyne Registry R1: the pre-registered universe. Every pair, its expected direction and lag window are fixed here."""
TARGETS = {  # id: (name, kind)
 "PCU334413334413": ("US semiconductor prices (PPI, semiconductor devices)", "price"),
 "PCU33443344":     ("US electronic component prices (PPI)", "price"),
 "PCU334111334111": ("US computer and server prices (PPI, electronic computers)", "price"),
 "IPG3344S":        ("US semiconductor and component production", "activity"),
 "A34SNO":          ("US new orders, computers and electronic products", "activity"),
}
CONTROL = "INDPRO"
# id: (name, ring, class, transform)   class decides the expected direction
EXTERNALS = {
 "PCU335311335311": ("Power transformer prices (PPI)", 1, "cost", "dlog"),
 "PCOPPUSDM": ("Copper price", 2, "cost", "dlog"),
 "PALUMUSDM": ("Aluminum price", 2, "cost", "dlog"),
 "PNICKUSDM": ("Nickel price", 2, "cost", "dlog"),
 "PTINUSDM":  ("Tin price (solder)", 2, "cost", "dlog"),
 "PZINCUSDM": ("Zinc price", 2, "cost", "dlog"),
 "PCU325120325120": ("Industrial gas prices, incl. helium (PPI)", 2, "cost", "dlog"),
 "IPMINE":   ("US mining production", 3, "cycle", "dlog"),
 "PCU333333": ("Machinery prices (PPI)", 3, "cost", "dlog"),
 "PCU483111483111": ("Deep-sea freight prices (PPI)", 3, "cost", "dlog"),
 "PCU481112481112": ("Air freight prices (PPI)", 3, "cost", "dlog"),
 "TSIFRGHT": ("US freight transportation volume index", 3, "cycle", "dlog"),
 "DCOILWTICO": ("Crude oil, WTI", 3, "cost", "dlog"),
 "MHHNGSP":  ("Natural gas, Henry Hub", 3, "cost", "dlog"),
 "PCU221122221122": ("Electric power distribution prices (PPI)", 3, "cost", "dlog"),
 "WPU0543":  ("Industrial electric power prices (PPI)", 3, "cost", "dlog"),
 "IPG2211S": ("US electric power generation", 3, "load", "dlog"),
 "DEXKOUS":  ("Korean won per US dollar", 4, "fx", "dlog"),
 "DEXTAUS":  ("Taiwan dollar per US dollar", 4, "fx", "dlog"),
 "DEXJPUS":  ("Japanese yen per US dollar", 4, "fx", "dlog"),
 "DEXCHUS":  ("Chinese yuan per US dollar", 4, "fx", "dlog"),
 "DTWEXBGS": ("Broad US dollar index", 4, "fx", "dlog"),
 "IMP5830":  ("US imports from Taiwan", 4, "flow_core", "dlog"),
 "IMPKR":    ("US imports from South Korea", 4, "flow_core", "dlog"),
 "IMPCH":    ("US imports from China", 4, "flow", "dlog"),
 "IMPJP":    ("US imports from Japan", 4, "flow", "dlog"),
 "ONI":      ("El Niño index (ONI)", 4, "weather", "level"),
 "AZ_PDSI":  ("Arizona drought index (fab water)", 4, "weather", "level"),
 "IPG3361T3S": ("US motor vehicle production (competing chip demand)", 5, "compete", "dlog"),
 "ALTSALES": ("US light vehicle sales", 5, "compete", "dlog"),
 "HOUST":    ("US housing starts (competing copper and electrical demand)", 5, "cycle", "dlog"),
 "PMAIZMTUSDM": ("Corn price (competing water and energy)", 5, "cycle", "dlog"),
 "PWHEAMTUSDM": ("Wheat price", 5, "cycle", "dlog"),
 "PURANUSDM": ("Uranium price", 5, "cost", "dlog"),
}
PLACEBOS = {"PLACEBO_1": 101, "PLACEBO_2": 202, "PLACEBO_3": 303}  # seeded random walks, no possible connection

# expected sign of the effect on the target: +, -, or ± (two-sided)
DIRECTION = {
 ("cost", "price"): "+", ("cost", "activity"): "±",
 ("cycle", "price"): "±", ("cycle", "activity"): "±",
 ("load", "price"): "±", ("load", "activity"): "+",
 ("fx", "price"): "-", ("fx", "activity"): "±",
 ("flow_core", "price"): "±", ("flow_core", "activity"): "+",
 ("flow", "price"): "±", ("flow", "activity"): "±",
 ("weather", "price"): "±", ("weather", "activity"): "±",
 ("compete", "price"): "+", ("compete", "activity"): "±",
}
def lag_window(ring): return (1, 6) if ring <= 3 else (1, 12)

def pairs():
    out = []
    for t, (tn, kind) in TARGETS.items():
        for x, (xn, ring, cls, tr) in EXTERNALS.items():
            lo, hi = lag_window(ring)
            out.append(dict(target=t, external=x, ring=ring, direction=DIRECTION[(cls, kind)], lag_lo=lo, lag_hi=hi, transform=tr))
        for x in PLACEBOS:
            out.append(dict(target=t, external=x, ring=0, direction="±", lag_lo=1, lag_hi=12, transform="dlog"))
    return out

if __name__ == "__main__":
    import csv
    ps = pairs()
    with open("hypotheses_R1.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ps[0].keys())); w.writeheader(); w.writerows(ps)
    print(len(ps), "pairs")
