#!/usr/bin/env python3
"""Build LaTeX tables and appendix bibliography for the preprint from the released tables."""
import re
import pandas as pd

T = "/home/claude/fertile-or-barren/paper/tables/"
OUT = "/tmp/claude-0/ms/preprint/"

JABBR = {
    "Economic Geology": "Econ. Geol.", "The Canadian Mineralogist": "Can. Mineral.",
    "Geology of Ore Deposits": "Geol. Ore Deposits", "Ore Geology Reviews": "Ore Geol. Rev.",
    "International Geology Review": "Int. Geol. Rev.", "International Journal of Earth Sciences": "Int. J. Earth Sci.",
    "Mineralium Deposita": "Miner. Deposita", "Lithos": "Lithos", "Chemical Geology": "Chem. Geol.",
    "Mineralogy and Petrology": "Mineral. Petrol.", "Geoscience Frontiers": "Geosci. Front.",
    "Journal of African Earth Sciences": "J. Afr. Earth Sci.", "Doklady Earth Sciences": "Dokl. Earth Sci.",
    "Journal of Asian Earth Sciences": "J. Asian Earth Sci.", "Geochemistry International": "Geochem. Int.",
    "Platinum Metals Review": "Platinum Met. Rev.", "Exploration and Mining Geology": "Explor. Min. Geol.",
    "Island Arc": "Isl. Arc", "Journal of Petrology": "J. Petrol.", "Precambrian Research": "Precambrian Res.",
    "Contributions to Mineralogy and Petrology": "Contrib. Mineral. Petrol.",
    "Journal of South American Earth Sciences": "J. S. Am. Earth Sci.", "Minerals": "Minerals",
    "Mineralogical Magazine": "Mineral. Mag.", "American Mineralogist": "Am. Mineral.",
}


def tex(s):
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}")]:
        s = s.replace(a, b)
    s = s.replace("‐", "-").replace("–", "--").replace("—", "---")
    s = s.replace(">=", r"$\geq$").replace("Δ", r"$\Delta$").replace("|", r"$|$")
    s = re.sub(r"(\d) - (\d)", r"\1--\2", s)
    s = re.sub(r"(\d\.\d\d)-(\d\.\d\d)", r"\1--\2", s)
    s = s.replace("References [23290], [24352]", "GEOROC references 23290 and 24352")
    return s


def initials(given):
    parts = re.findall(r"[A-Z][a-z]?\.|[A-Z]\b", given)
    out = []
    for g in re.split(r"\.\s*", given.strip().rstrip(".")):
        if not g:
            continue
        if "-" in g:
            out.append("-".join(x + "." for x in g.split("-") if x))
        else:
            out.append(g + ".")
    return " ".join(out) if out else given


def fmt_authors(au):
    au = au.strip()
    if au.startswith("U.S. Geological Survey"):
        return "U.S. Geological Survey"
    etal = au.endswith("et al.")
    au = re.sub(r",?\s*et al\.$", "", au)
    pairs = re.findall(r"([^,]+?), ((?:[A-Z][a-z]?\.?-?\s?)+)(?:,|$)", au)
    names = [f"{initials(g)} {l.strip()}" for l, g in pairs]
    if not names:
        return au
    if etal:
        return f"{names[0]} et al."
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def fmt_ref(r):
    m = re.match(r"^(?P<au>.+?) \((?P<yr>\d{4}[a-z]?)\)\. (?P<rest>.+)$", r.strip())
    au, yr, rest = m["au"], m["yr"], m["rest"]
    doi = url = None
    if " https://doi.org/" in rest:
        rest, doi = rest.rsplit(" https://doi.org/", 1)
    elif " https://" in rest:
        rest, url = rest.rsplit(" https://", 1)
        url = "https://" + url
    rest = rest.strip().rstrip(".")
    title, cont = rest.rsplit(". ", 1) if ". " in rest else (rest, "")
    cm = re.match(r"^(?P<j>.*?)(?: (?P<v>\d[\d\-]*))?(?:, (?P<p>[\w\-]+))?$", cont)
    j, v, p = cm["j"], cm["v"], cm["p"]
    if not v and not p and re.match(r"^(Reston|Springer)", cont):
        j = cont
    jj = JABBR.get(j, j)
    A = tex(fmt_authors(au))
    s = f"{A}{'' if A.endswith('.') else '.'} {tex(title)}. \\textit{{{tex(jj)}}}"
    if v:
        s += f", {v}"
        if p:
            s += f":{p.replace('-', '--')}"
    elif p:
        s += f", {p.replace('-', '--')}"
    s += f", {yr[:4]}."
    if doi:
        s += f" \\doi{{{doi}}}."
    if url:
        s += f" \\url{{{url}}}."
    return s, (doi or url or "").lower()


def main():
    # ---- Appendix references (Table S1) ----
    main_dois = {"10.1007/978-3-662-08444-1": "naldrett2004", "10.2113/econgeo.108.8.1833": "gao2013",
                 "10.5066/p1ylgluz": "parks2026", "https://mrdata.usgs.gov/mrds/": "usgs2005"}
    t = pd.read_csv(T + "TableS1_FertileWeak.csv")
    keys, items = {}, []
    for r in t["Reference"]:
        for p in [x.strip() for x in r.split(" ; ") if x.strip()]:
            s, ident = fmt_ref(p)
            if ident in main_dois:
                keys[p] = main_dois[ident]
                continue
            if p not in keys:
                k = f"s1ref{len(items) + 1}"
                keys[p] = k
                items.append((k, s))
    with open(OUT + "refs_s1.tex", "w") as f:
        for k, s in items:
            f.write(f"\\bibitem{{{k}}} {s}\n\n")
    rows = []
    for _, r in t.iterrows():
        ks = ",".join(dict.fromkeys(keys[p.strip()] for p in r["Reference"].split(" ; ") if p.strip()))
        name = r["Intrusion"].title().replace("Dyke Zimbabwe", "Dyke")
        rows.append(f"{tex(name)} & {r['Label'][0]} & {r['Samples']:,} & {tex(r['Deposit / occurrence'])} & "
                    f"{tex(r['Deposit type'])} & \\cite{{{ks}}} \\\\")
    with open(OUT + "tab_s1.tex", "w") as f:
        f.write("\n".join(rows))

    # ---- Table 1: leaderboard ----
    lb = pd.read_csv(T + "Table6_Leaderboard.csv")
    rows = []
    for _, r in lb.iterrows():
        c = [tex(r["Index"])] + [("--" if r[k] == "insufficient" else tex(r[k])) for k in
                                 ["All samples", "Cumulates", "Chilled margins + fine-grained dikes/sills",
                                  "Altered", "Unresolved type"]] + [tex(r["Fertile / barren intrusions (all)"]),
                                                                    tex(r["Coverage (all)"])]
        rows.append(" & ".join(c) + r" \\")
    open(OUT + "tab_leaderboard.tex", "w").write("\n".join(rows))

    # ---- Robustness ----
    rb = pd.read_csv(T + "Table7_Robustness.csv", dtype=str).fillna("--")
    open(OUT + "tab_robust.tex", "w").write("\n".join(" & ".join(tex(x) for x in r) + r" \\" for r in rb.values))

    # ---- Selection ----
    se = pd.read_csv(T + "Table2_Selection.csv")
    rows = []
    for st, n in se.values:
        ind = st.startswith("  ")
        lab = tex(st.strip()).replace("removed: ", "")
        lab = (r"\quad $-$ " + lab) if ind else lab
        rows.append(f"{lab} & {abs(int(n)):,} \\\\")
    open(OUT + "tab_selection.tex", "w").write("\n".join(rows))

    # ---- Labels ----
    la = pd.read_csv(T + "Table3_Labels.csv")
    open(OUT + "tab_labels.tex", "w").write(
        "\n".join(f"{a} & {b} & {c:,} & {d:,} \\\\" for a, b, c, d in la.values))

    # ---- Sample types ----
    stt = pd.read_csv(T + "Table4_SampleTypes.csv")
    open(OUT + "tab_types.tex", "w").write("\n".join(" & ".join(tex(x) for x in r) + r" \\" for r in stt.values))

    # ---- Corrections ----
    co = pd.read_csv(T + "TableS3_Corrections.csv").fillna("")
    open(OUT + "tab_corr.tex", "w").write("\n".join(" & ".join(tex(x) for x in r) + r" \\" for r in co.values))
    print(len(items), "appendix references")


if __name__ == "__main__":
    main()
