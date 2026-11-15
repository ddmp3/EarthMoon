"""Shared configuration: canonical variable names, aliases, feature list, known analog sites."""

# Canonical name -> substrings/aliases used to match raw NetCDF variable names (case-insensitive).
# NOTE: in NLDAS-2, the Noah L4 product (NLDAS_NOAH0125_H) holds surface/soil/flux variables,
# while wind and surface pressure live in the FORCING product (NLDAS_FORA0125_H). Audit both.
VARIABLE_ALIASES = {
    "skin_temp":     ["avgsurft", "skin", "lst", "surft", "tskin"],
    "soil_moist":    ["soilm_0_10", "soilm", "soil_moist", "rootmoist", "smc"],
    "sw_net":        ["swnet", "swdown", "sw_net", "dswrf"],
    "lw_net":        ["lwnet", "lwdown", "lw_net", "dlwrf"],
    "albedo":        ["albedo"],
    "wind_u":        ["wind_e", "ugrd", "u10"],
    "wind_v":        ["wind_n", "vgrd", "v10"],
    "pressure":      ["psurf", "pres", "sp"],
    "snow_depth":    ["snowdepth", "snod", "swe"],
    "soil_temp":     ["soilt_", "tsoil"],
}

# Feature vector used from Phase 3 onward (one row per grid cell).
# 'dimensionless' ones are comparable across planets; 'absolute' ones are Earth-only context.
FEATURES_THERMAL = ["t_mean", "t_amp", "t_p05", "t_p95", "amp_ratio"]       # amp_ratio = t_amp / t_mean (dimensionless)
FEATURES_RADIATIVE = ["sw_net_mean", "lw_net_mean", "ati"]                 # ati = apparent thermal inertia proxy
FEATURES_GEOMETRIC = ["slope_deg", "roughness_m", "shadow_frac"]
FEATURES_ATMOS = ["pressure_pa", "wind_mean"]                               # Earth-only; meaningless for the Moon
FEATURES_CRYO = ["freeze_thaw_days", "soil_moist_mean"]                    # permafrost / Mars-ice analog context

# Features that can be matched against a lunar reference (Phase 5)
FEATURES_LUNAR_MATCH = ["amp_ratio", "ati", "slope_deg", "roughness_m", "shadow_frac", "t_p05"]

# Approximate coordinates of classical analog sites (lat, lon) -- used only to measure novelty.
KNOWN_ANALOGS = {
    "Devon Island (Haughton)": (75.4, -89.8),
    "Atacama (Yungay)": (-24.1, -70.0),
    "Antarctic Dry Valleys": (-77.5, 162.5),
    "Mauna Kea": (19.82, -155.47),
    "Svalbard": (78.2, 15.6),
    "Rio Tinto": (37.7, -6.55),
    "MDRS Utah": (38.4, -110.8),
    "Death Valley": (36.5, -116.9),
}
