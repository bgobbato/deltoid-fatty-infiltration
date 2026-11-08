"""DFDI: measurement engine for the Deltoid Fatty Degeneration Index (Rescigno et al. 2026).

Given a CT (NIfTI, in HU) and a manual deltoid mask (NIfTI, same grid), computes
CSA, mean HU, extra fatty-infiltration metrics and the DFDI.
"""

__version__ = "0.1.0"

# Values published in the article (Table 1, n=100). Use only as an approximation:
# the article standardizes z-scores within its own cohort, on a single scanner.
ARTICLE_REFERENCE = {
    "name": "article_rescigno_2026_approx",
    "hu_mean": 42.9,
    "hu_sd": 3.8,
    "csa_mean": 3651.6,
    "csa_sd": 662.2,
    "n": 100,
}
