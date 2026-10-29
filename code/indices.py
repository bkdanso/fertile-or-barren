"""indices.py - the published fertility indices scored on the benchmark.

Plain-language note: each entry below is one "ore-potential formula". It says which
elements it needs, how it is calculated, and which direction is supposed to mean
"more likely to host ore" according to the paper that proposed it. The scoring
program uses these definitions exactly, so anyone can check them. Directions and
references were checked against Crossref metadata (Oct 2026).

Convention: every function returns a score where HIGHER = predicted MORE FERTILE.
If the published hypothesis says a LOW ratio means fertile, the score is the negative
(log) ratio. Ratios are log10-transformed so that scores are well behaved.
"""
import numpy as np
import pandas as pd

PPM = "(PPM)"
# Primitive-mantle reference values (McDonough & Sun 1995, Chem. Geol. 120:223-253, doi:10.1016/0009-2541(94)00140-4)
PM = {"CU": 30.0, "PD": 0.0039, "IR": 0.0032, "PT": 0.0071, "TH": 0.0795, "NB": 0.658}


def col(d, el):
    """Element concentration in ppm, merging ppm and wt% columns where GEOROC splits them."""
    c = d.get(el + PPM)
    s = pd.to_numeric(c, errors="coerce") if c is not None else pd.Series(np.nan, index=d.index)
    if el == "S" and "S(WT%)" in d:
        s = s.fillna(pd.to_numeric(d["S(WT%)"], errors="coerce") * 1e4)
    if el == "NI" and "NIO(WT%)" in d:
        s = s.fillna(pd.to_numeric(d["NIO(WT%)"], errors="coerce") * 1e4 * 58.693 / 74.692)
    return s.where(s > 0)


def lratio(d, a, b):
    return np.log10(col(d, a) / col(d, b))


def ni_depletion(d):
    """Negative residual of log10(Ni) from a label-free quadratic Ni-MgO trend fitted on all
    benchmark samples (olivine control). Depleted Ni at a given MgO = Ni lost to sulfide."""
    mg = pd.to_numeric(d.get("MGO(WT%)"), errors="coerce")
    ni = np.log10(col(d, "NI"))
    ok = mg.between(5, 50) & ni.notna()
    if ok.sum() < 30:
        return pd.Series(np.nan, index=d.index)
    coef = np.polyfit(mg[ok], ni[ok], 2)
    resid = ni - np.polyval(coef, mg)
    return -resid.where(mg.between(5, 50))


INDICES = [
    # id, family, needs, function, published hypothesis, reference
    dict(id="cu_pd", family="Chalcophile ratio", needs=["CU", "PD"],
         f=lambda d: lratio(d, "CU", "PD"),
         hypothesis="High Cu/Pd (above mantle) = PGE stripped by earlier sulfide = fertile",
         ref="Barnes, Couture, Sawyer & Bouchaib 1993, Econ. Geol. 88:1402-1418, doi:10.2113/gsecongeo.88.6.1402; Li, Maier & de Waal 2001, S. Afr. J. Geol. 104:309-318, doi:10.2113/gssajg.104.4.309"),
    dict(id="cu_pd_dev", family="Chalcophile ratio (exploratory)", needs=["CU", "PD"],
         f=lambda d: (lratio(d, "CU", "PD") - np.log10(PM["CU"] / PM["PD"])).abs(),
         hypothesis="Any departure of Cu/Pd from mantle (high = depleted, low = sulfide-enriched) = sulfide involvement",
         ref="Benchmark variant of Cu/Pd (two-sided form) defined by the benchmark authors; mantle Cu/Pd from McDonough & Sun 1995"),
    dict(id="pd_ir", family="Chalcophile ratio", needs=["PD", "IR"],
         f=lambda d: lratio(d, "PD", "IR"),
         hypothesis="High Pd/Ir = fractionated, sulfide-associated PGE signature = fertile",
         ref="Barnes, Naldrett & Gorton 1985, Chem. Geol. 53:303-323, doi:10.1016/0009-2541(85)90076-2"),
    dict(id="pt_pd", family="Chalcophile ratio (exploratory)", needs=["PT", "PD"],
         f=lambda d: -lratio(d, "PT", "PD"),
         hypothesis="Low Pt/Pd = Pd-rich, sulfide-associated PGE = fertile (exploratory)",
         ref="Exploratory ratio; direction set by the benchmark authors (Oct 2026), not taken from a single published fertility test"),
    dict(id="cu_zr", family="Chalcophile ratio", needs=["CU", "ZR"],
         f=lambda d: -lratio(d, "CU", "ZR"),
         hypothesis="Low Cu/Zr = Cu depleted relative to an incompatible element = sulfide removed = fertile",
         ref="Lightfoot et al. 1990, Contrib. Mineral. Petrol. 104:631-644, doi:10.1007/bf01167284"),
    dict(id="ni_cu", family="Chalcophile ratio (exploratory)", needs=["NI", "CU"],
         f=lambda d: -lratio(d, "NI", "CU"),
         hypothesis="Low Ni/Cu = Cu-rich, sulfide-fractionated signature (exploratory)",
         ref="Exploratory ratio; direction set by the benchmark authors (Oct 2026), not taken from a single published fertility test"),
    dict(id="ni_depletion", family="Ni depletion", needs=["NI", "MGO"],
         f=ni_depletion,
         hypothesis="Ni below the olivine-controlled Ni-MgO trend = Ni lost to sulfide = fertile",
         ref="Li & Naldrett 1999, Lithos 47:1-31, doi:10.1016/s0024-4937(99)00005-5; Barnes & Lightfoot 2005, Econ. Geol. 100th Anniv. Vol.:179-213, doi:10.5382/av100.08"),
    dict(id="th_nb", family="Crustal contamination", needs=["TH", "NB"],
         f=lambda d: lratio(d, "TH", "NB"),
         hypothesis="High Th/Nb = crustal contamination, a common trigger of sulfide saturation = fertile. "
                    "Note: Th/Yb above the Nb/Yb mantle array (Pearce 2008) with unit slope ranks samples identically.",
         ref="Lightfoot et al. 1993, Contrib. Mineral. Petrol. 114:171-188, doi:10.1007/bf00307754; Pearce 2008, Lithos 100:14-48, doi:10.1016/j.lithos.2007.06.016"),
    dict(id="la_sm", family="Crustal contamination", needs=["LA", "SM"],
         f=lambda d: lratio(d, "LA", "SM"),
         hypothesis="High La/Sm = LREE enrichment from crustal contamination = fertile",
         ref="Lightfoot et al. 1990, Contrib. Mineral. Petrol. 104:631-644, doi:10.1007/bf01167284"),
    dict(id="zr_y", family="Crustal contamination (exploratory)", needs=["ZR", "Y"],
         f=lambda d: lratio(d, "ZR", "Y"),
         hypothesis="High Zr/Y = enriched/contaminated source (exploratory)",
         ref="Exploratory ratio; direction set by the benchmark authors (Oct 2026), not taken from a single published fertility test"),
    dict(id="s", family="Sulfur", needs=["S"],
         f=lambda d: np.log10(col(d, "S")),
         hypothesis="High whole-rock S = sulfide present = fertile",
         ref="Barnes & Lightfoot 2005, Econ. Geol. 100th Anniv. Vol.:179-213, doi:10.5382/av100.08"),
    dict(id="s_se", family="Sulfur", needs=["S", "SE"],
         f=lambda d: lratio(d, "S", "SE"),
         hypothesis="S/Se above mantle range = external crustal S added = fertile",
         ref="Queffurus & Barnes 2015, Ore Geol. Rev. 69:301-324, doi:10.1016/j.oregeorev.2015.02.019"),
]


def compute_all(d):
    """Return a DataFrame with one column per index (higher = predicted more fertile)."""
    out = pd.DataFrame(index=d.index)
    for ix in INDICES:
        out[ix["id"]] = ix["f"](d).replace([np.inf, -np.inf], np.nan)
    return out


# Display names for figures and tables: element symbols capitalised as in the periodic table.
# An asterisk marks the four exploratory indices (direction set by the authors, not a published test).
DISPLAY = {
    "cu_pd": "Cu/Pd",
    "cu_pd_dev": "|Δlog(Cu/Pd)|*",
    "pd_ir": "Pd/Ir",
    "pt_pd": "Pt/Pd*",
    "cu_zr": "Cu/Zr",
    "ni_cu": "Ni/Cu*",
    "ni_depletion": "Ni depletion (vs MgO)",
    "th_nb": "Th/Nb",
    "la_sm": "La/Sm",
    "zr_y": "Zr/Y*",
    "s": "S",
    "s_se": "S/Se",
}
