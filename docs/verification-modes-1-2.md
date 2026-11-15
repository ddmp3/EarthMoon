# Vérification des modes 1 et 2 (Wassim)

> Conversion en Markdown de `Sample 2.docx` (PR #47, Wassim, 14/11/2026). Le texte d'origine, en anglais, est conservé tel quel à partir de la section « Mission briefing ».
>
> **Ce qui est déjà appliqué** dans [scenarios.md](scenarios.md) : les points marqués RESOLVED (justification des critères volcaniques, températures présentées comme des proxys).
>
> **Décisions d'équipe à prendre** (aucune valeur du moteur n'a été changée) :
> 1. `slope_mean` (mode 1) : passer de 5–15° à 3–10° ? Les traversées réelles d'Apollo 15 et 16 avaient une pente moyenne de 4,5 à 5,6°.
> 2. `lst_amplitude` (modes 1 et 2) : seuil trop faible face aux ~300 K d'amplitude lunaire à basse latitude ; le relever ou le renommer.
> 3. `t2m_mean` du forage (mode 2) : passer de ≤ 0 °C à ≤ -10 °C ?
> 4. `quake_count` (mode 2) : fixer le seuil après avoir regardé la distribution réelle sur les 7 sites de validation. Un faible nombre USGS peut refléter peu de stations plutôt qu'un sol calme.
> 5. Pente : les pentes d'Apollo viennent d'un modèle de terrain à 2 m, Copernicus DEM est à ~30 m. Calculer la pente de la même façon côté Terre et côté Lune.
>
> **Pistes canadiennes à intégrer** : Mistastin Lake (anorthosite, analogue des hautes terres lunaires), cratère Tunnunik, jeu de données de navigation de rover de l'île Devon, RADARSAT-1 et RCM.

---

## Where on Earth could you test a lunar rover without leaving the planet?

Task 1: Verification of Modes 1 and 2 (scenarios.md). NASA Space Apps 2026, Terrestrial Analogs. Prepared for Wassim (robotics, instruments and data). Draft for team review.

How to read this: every row of Modes 1 and 2 is checked against published specs. Green = confirmed or keep. Yellow = logic only or unverified. Orange = needs a change or a team decision. Proposed values are recommendations, not facts.

Updated 14 Nov 2026 with NASA, ISRO and Canadian Space Agency (CSA) sources. Section 6 onward is new.

## Mission briefing: five surprises from the data

1. **Rovers drive gently.** Apollo's rover was rated for 25° slopes, yet its real traverses averaged only 4.5 to 5.6°. Our first mean-slope range was too steep.
2. **The south pole is not volcanic.** NASA's geology team says the pole sits in highlands crust. The best Earth rock twin may be the anorthosite at Mistastin Lake in Labrador, a lunar analogue the CSA has funded since 2010.
3. **Lunar soil is a thermal blanket.** India's Chandrayaan-3 lander probed the south polar soil: about -10 °C at 10 cm depth against warmer temperatures at the surface. Moon dust is an excellent insulator.
4. **The cold is beyond Earth.** NASA's Artemis rover must spend up to 2 hours in permanently shadowed craters below -180 °C. No place on Earth gets that cold, so every temperature row in our app is a proxy.
5. **A famous NASA dataset has a polar blind spot.** NASA's SRTM elevation data stops at 60°N and 56°S, so it misses the Dry Valleys, Haughton Crater and Svalbard. This is why scenarios.md uses Copernicus DEM.

## 1. Mode 1: Rover mobility

| Parameter | Current value | Status / new value | Evidence and source | Reason |
|---|---|---|---|---|
| slope_mean | 5 to 15°, tol 10°, w3 | PROPOSED: 3 to 10° (team to agree, set tolerance) | Apollo 15/16 rover traverses had mean slopes of 4.5 to 5.6° (NASA NTRS 20250011301). Rover limits of 15 to 25° are local slopes. | A 15° mean over a 1 km window is extreme terrain. Real traverses were gentle. |
| slope_max | 15 to 30°, tol 10°, w1 | CONFIRMED | VIPER: 15° design limit, 25 to 30° if needed (NTRS 20240013903, 20250004148; science.nasa.gov/mission/viper). Apollo LRV: 25° (NASA SP-4214 ch.13). Yutu-2: 20° (CGTN, 2022, secondary). NASA LTV requirement: 20° (section 6). | Range brackets all three rovers' limits. |
| roughness | 5 to 40 m, tol 30 m, w2 | NOT SOURCEABLE from rover specs. Justify with LOLA data. | Rover specs give obstacle height only: VIPER 15 to 20 cm, Yutu-2 20 cm, LRV 30 cm. | Std dev of altitude over 1 km is a different scale from obstacle height. |
| precipitation | ≤ 1 mm/day, w1 | LOGIC ONLY | No source. The Moon has no water. | Proxy for dry, loose soil. State this. |
| t2m_min | ≤ -20 °C, tol 20, w1 | KEEP, label as a cold-soak proxy | Diviner: permanently shadowed craters reach 29 to 50 K (Paige et al. 2010, Science 330, 479; EPSC2013-386). | No place on Earth approaches lunar polar cold. |
| lst_amplitude | ≥ 20 °C, tol 15, w1 | TOO WEAK: raise or relabel (team decision) | Diviner: equatorial surface near 400 K at noon, under 100 K at night (EPSC2013-386). | Real lunar swing is about 300 K at low latitude. |
| volcano_distance | ≤ 50 km, tol 100, w1 | REWORD the rationale | VERIFIED: NASA Artemis geology researchers place the south pole in highlands crust near the South Pole-Aitken basin (Moriarty and Petro, EPSC2022-295). See section 6. | South pole is mostly highland, not mare basalt. Say basalt is an Earth stand-in for regolith and rock mechanics. |

## 2. Mode 2: Instrument calibration

| Parameter | Current value | Status / new value | Evidence and source | Reason |
|---|---|---|---|---|
| Drill: t2m_mean | ≤ 0 °C, tol 10, w2 | WEAK: consider ≤ -10 °C | VIPER's TRIDENT drill was tested in soil with 5% water chilled to -100 °C (NTRS 20205000864). | 0 °C air temperature is barely frozen. Remains a proxy for ice-cemented ground. |
| Drill: volcano_distance | ≤ 50 km, tol 100, w1 | REWORD the rationale | Same as Mode 1. | Same highland caveat. |
| Wind: wind | ≤ 3 m/s, tol 3, w2 | LOGIC ONLY | No source. The Moon has no atmosphere. | Calm baseline for wind instruments. |
| Gas: humidity | ≤ 40%, tol 30, w2 | LOGIC ONLY | No source. | Dry-atmosphere proxy. |
| Gas: precipitation | ≤ 0.5 mm/day, tol 1, w1 | LOGIC ONLY | No source. | Dry-environment proxy. |
| Seismo: quake_count | ≤ 5 (M≥2.5, 300 km, since 2000), tol 20, w3 | UNVERIFIED threshold: test on the 7 validation sites first | Apollo saw 28 shallow moonquakes in 8 years (Nakamura, NTRS 19930008250). No sustained microseisms, so sensitivity 100 to 1000x Earth's (Latham et al., Cambridge/NTRS 19780005006). Instrument sensitivity confirmed at 0.3 nm (NASA Apollo 12 Preliminary Science Report, section 6). | Low USGS count can mean few stations, not quiet ground. Catalog is less complete in remote regions. |
| Thermal: lst_amplitude | ≥ 25 °C, tol 15, w2 | TOO WEAK | Diviner values above. | Same as Mode 1. |
| Thermal: t2m_min | ≤ -30 °C, tol 20, w1 | KEEP, label as cold-soak proxy | Diviner values above. | Same as Mode 1. |

## 3. Reference: lunar rover specifications

| Rover | Slope capability | Obstacle height | Source |
|---|---|---|---|
| Apollo LRV | Climbs and descends 25°, parks on 35° | 30 cm | NASA SP-4214, chapter 13 (apolloexplorer.co.uk/books/sp-4214/ch13-3.html) |
| VIPER (cancelled) | 15° requirement; 25 to 30° if needed, with more slipping | 15 cm (req), 20 cm (design limit) | NASA NTRS 20240013903; 20250004148; science.nasa.gov/mission/viper |
| Yutu-2 (China) | 20° | 20 cm | CGTN 2022-09-11 (secondary, quotes designers) |
| NASA LTV (planned, Artemis) | Must traverse 20° slopes and spend up to 2 hours in permanently shadowed regions | n/a | NASA LTV solicitation on SAM.gov, as summarized by jatan.space Moon Monday #171 (secondary). Open the original before quoting. |
| Pragyan (India) | Not found | Not found | Searched but no slope specification located. Do not quote a number. |

Real traverse data: Apollo 15 and 16 rover routes had mean slopes of 5.6° and 4.5° and maximum slopes of 22.1° and 24.7°, measured on a 2 m terrain model (NASA NTRS 20250011301, LPSC 2026 abstract).

## 4. Reference: lunar temperatures (Diviner)

| Quantity | Value | Source |
|---|---|---|
| Equatorial surface, noon | about 400 K | Diviner overview, EPSC2013-386 |
| Equatorial surface, night | under 100 K | Diviner overview, EPSC2013-386 |
| Permanently shadowed craters, annual max | approaching 50 K | Diviner overview, EPSC2013-386 |
| Coldest measured mid-day crater floors | as low as 29 K | Paige et al. 2010, Science 330, 479 |
| Water-ice persistence threshold | max surface temp below 110 K | Paige et al. 2010; Williams et al. 2019, JGR Planets |

## 5. Issues to raise with the team

- **Slope baseline mismatch:** Apollo values come from a 2 m terrain model, while Copernicus DEM is about 30 m. Slope computed on a coarser grid is smoother, so confirm that slope_mean and slope_max are computed the same way for Earth and Moon.
- **Seismometer sensitivity discrepancy:** RESOLVED. Use 0.3 nm. NASA's Apollo 12 Preliminary Science Report states it. The 1 angstrom figure came from an early review paper and conflicts with it (details in section 6).
- **quake_count threshold:** run it on the 7 validation sites and look at the real distribution before fixing the cutoff.
- **Temperature rows are proxies.** Earth cannot reproduce lunar polar cold or the roughly 300 K day/night swing. Say this in the app's site card.
- **Volcano rows:** RESOLVED. The south pole is highlands crust, not mare basalt. Reword the rationale: basalt is an Earth stand-in for regolith and rock mechanics, and the best rock twin for the highlands is anorthosite (section 6 and 8).

## 6. Fact-check results (14 Nov 2026)

Every item that was flagged "not yet verified" earlier, with what was found and what to do next.

| Item | Earlier status | What we found | Source | Action |
|---|---|---|---|---|
| Seismometer sensitivity | Conflict: 0.3 nm vs 1 angstrom | RESOLVED: use 0.3 nm. NASA's Apollo 12 Preliminary Science Report says the long-period seismometers detect ground motion as small as 0.3 nm at maximum sensitivity, and the short-period one 0.3 nm at 1 Hz. The 1 angstrom (0.1 nm) figure came from an early Apollo-team review paper. Why they differ was not determined. | NASA Apollo 12 Preliminary Science Report, ch. 3 (an.rsl.wustl.edu/apollo/data/a12/stationLM/pse/docs/pse_psr.pdf) | Quote 0.3 nm. |
| South pole geology | Unchecked | CONFIRMED: NASA Artemis researchers describe the south pole as set within highlands crust, near the 2000 km South Pole-Aitken basin. Highland rock is mostly anorthosite (plagioclase-rich), while mare basalt is mainly a nearside feature. So "basaltic substrate" is wrong as a south pole rationale. | Moriarty and Petro, Europlanet Science Congress 2022, EPSC2022-295 | Reword the volcano rows. Add a lithology note (anorthosite) in candidates.json. |
| LTV requirements | Not found | FOUND: NASA's solicitation asks the Lunar Terrain Vehicle to traverse 20° slopes, spend up to 2 hours in permanently shadowed regions (well below -180 °C), and drive up to 20 km on an 8-hour round trip with two suited astronauts. Source is a secondary summary of the SAM.gov document. | NASA news release "NASA Selects Companies to Advance Moon Mobility for Artemis Missions"; jatan.space Moon Monday #171 | slope_max range stays. Add 20° as an anchor. Open the SAM.gov original before quoting. |
| PRIME-1 drill | Not found | PARTIAL: NASA reports TRIDENT demonstrated its full range of motion on the Moon (rotation, extension, percussion, heater). The lander tipped on its side about 400 to 500 m from the Mons Mouton target and ran roughly 12 hours instead of 10 days. The mass spectrometer detected only gases of human origin. No ice-drilling result was found. | NASA "NASA's Lunar Drill Technology Passes Tests on the Moon"; NASA NTRS 20260003150 (MSolo results, Apr 2026) | Drill ranges unchanged. Do not claim PRIME-1 validated ice drilling. |
| India: Chandrayaan-3 | Not searched | PARTIAL: Pragyan slope spec not found. But the ChaSTE probe gave the first in-situ south polar soil temperatures (69.37°S). Flat-ground surface read about 332 K, matching the orbiter value of about 330 K. The probe sat on a 6° sunward slope and read warmer. ISRO's first graph spanned about -10 °C to 60 °C over the top 10 cm. | ISRO, "India Bags Credit First-Ever In-Situ Measurement" (isro.gov.in); Commun. Earth Environ., doi 10.1038/s43247-025-02114-6 | Supports the temperature proxies. Slope changes temperature, another reason to compute slope consistently. |

## 7. NASA data for this challenge

Important: the official Space Apps Resources page could not be opened by my tools (the site blocks automated access). The list below comes from an independent summary, Space Data Atlas, which states it is not the official list. Please paste the official Resources section so it can be cross-checked. Also already in scenarios.md: LRO LOLA, MODIS (MOD11A2, MOD13A1) and NASA POWER from NASA, plus Copernicus DEM (ESA).

> Note (David, 15/11) : la liste officielle des Resources a depuis été récupérée. Elle cite NASA Earthdata Search, NASA Worldview, PDS, LRO (LROC, LOLA, Diviner, LEND, Mini-RF), Diviner, ASC (RCM, RADARSAT-1, tutoriel SAR Python), ESA (Copernicus Data Space Ecosystem, ESA Open Science Catalog) et JAXA G-Portal.

| Dataset | Provider | What it gives | How we could use it | Access |
|---|---|---|---|---|
| SRTMGL1 v003 elevation | NASA LP DAAC | About 30 m elevation, 60°N to 56°S | Slope and roughness as a NASA cross-check at mid-latitudes. Misses polar sites, so keep Copernicus DEM for those. | Earthdata Login to download |
| EMIT L2B mineral maps (EMITL2BMIN) | NASA LP DAAC | Surface minerals of Earth's arid regions from the ISS | Check whether desert candidates share minerals with Mars (compare to CRISM). Not yet in the parameter catalog. | Earthdata Login to download |
| HLS Landsat 30 m (HLSL30 v2.0) | NASA LP DAAC | Surface reflectance on a common 30 m grid | Confirm bare ground at site scale (supports the ndvi filter). | Earthdata Login to download |
| MRO CRISM mineral maps (MTRDR) | NASA PDS Geosciences | Mars clays, sulfates, other minerals | Mars-side minerals if the team adds a Mars target. | No login |
| Mars Trek tiles (CTX 5 m, MOLA 463 m) | NASA JPL Solar System Treks | Mars basemaps, open to web pages | Side-by-side visual of an Earth site and a Mars site. | No login |
| LRO Diviner polar temperature maps | NASA LRO Diviner team (UCLA) / PDS | Moon surface and polar temperatures | Direct source for moon-south-pole.json (with David). | No login |

## 8. Canada: Canadian Space Agency data, sites and programs

Canada has real analogue sites and real data to offer. Several are well placed to be the "understudied" favourites for Xavier's presentation (task 5). Coordinates and terrain statistics for Mistastin and Tunnunik have not been retrieved yet.

| Item | What it is | Why it matters to our app | Source |
|---|---|---|---|
| CSA analogue network (CARN) | CSA program of Canadian analogue sites. Nodes include the Haughton-Mars Project station on Devon Island (75°22'N, 89°41'W) and the McGill Arctic Research Station on Axel Heiberg Island (79°26'N, 90°46'W). | USEFUL: confirms our Haughton validation coordinate (75.4, -89.7) is right. | SpaceNews; IPY EOI page |
| Mistastin Lake, Labrador | CSA-funded lunar analogue missions since 2010. An exceptional geological lunar analogue with anorthosite and preserved impact ejecta. | USEFUL: the highland rock our volcanic criteria miss. Strong "understudied" candidate and a good story for Xavier. | IAC-12 abstract; Western University news |
| Tunnunik Crater, Victoria Island (NWT) | Arctic impact crater studied as a Moon and Mars analogue. Research funded in part by the CSA SOAR program. | USEFUL: second Canadian understudied candidate. | SpaceQ |
| Devon Island Rover Navigation Dataset | Open rover navigation data from Haughton, a Moon and Mars analogue (Univ. of Toronto, CSA CARN grant). | USEFUL: real rover data to test whether our slope and roughness ranges match actual driving. | ASRL, Univ. of Toronto |
| RADARSAT-1 and RADARSAT Constellation (RCM) open data | Over 36,000 RADARSAT-1 radar images released free in 2019. Archived RCM products are open (16 m and coarser on land) through NRCan's EODMS under the Open Government Licence. Check access terms on EODMS. | USEFUL: radar sees through cloud and polar night. A CSA complement to NASA optical and thermal data for Arctic candidates. | canada.ca news release; CSA open data portal; CEOS CSA update |
| Canada's Lunar Utility Vehicle (LUV) | Planned Canadian rover for logistics, spacewalk support and science. $1.2 billion over 13 years. Three firms (Canadensys, MDA Space, Mission Control) got $14.6 million in July 2025 for studies. Launch no earlier than 2033. | USEFUL: a real customer for Mode 1. Mobility validation is exactly the question these teams face. | CSA; SpaceQ |

## 9. Still open

- Pragyan slope specification: not found.
- NASA LTV figures come from a secondary summary. Open the original SAM.gov solicitation before quoting.
- PRIME-1 science results beyond the hardware demonstration: none found.
- Official Space Apps Resources list: not readable by my tools. Paste it to cross-check section 7. *(Fait depuis, voir la note de la section 7.)*
- Why the 0.3 nm and 1 angstrom seismometer figures differ: not determined.
- Claims marked LOGIC ONLY have no citation by design, but a reviewer may ask for a reference.

## 10. Source list

- NASA SP-4214, *Where No Man Has Gone Before*, ch.13: apolloexplorer.co.uk/books/sp-4214/ch13-3.html
- VIPER: science.nasa.gov/mission/viper/rover-and-instruments and /lunar-operations
- NASA NTRS 20240013903 (VIPER mobility, LSIC 2024); 20250004148 (VIPER 2025); 20205000864 (VIPER mission overview)
- NASA NTRS 20250011301 (Apollo LRV as-traversed metrics, LPSC 2026)
- CGTN, Yutu-2 work report, 11 Sep 2022
- Paige et al. 2010, Science 330, 479 (Diviner cold traps); Williams et al. 2019, JGR Planets (seasonal polar temperatures); EPSC2013-386 (Diviner overview)
- Latham et al., Results from the Apollo Passive Seismic Experiment, NTRS 19780005006; Nakamura, lunar seismicity, NTRS 19930008250
- NASA Apollo 12 Preliminary Science Report, Passive Seismic Experiment: an.rsl.wustl.edu/apollo/data/a12/stationLM/pse/docs/pse_psr.pdf
- Moriarty and Petro, Europlanet Science Congress 2022, EPSC2022-295 (Artemis and the lunar south pole)
- NASA news release, "NASA Selects Companies to Advance Moon Mobility for Artemis Missions"; jatan.space Moon Monday #171 (secondary summary of the LTV solicitation)
- NASA, "NASA's Lunar Drill Technology Passes Tests on the Moon"; NASA NTRS 20260003150 (MSolo overview and results, Apr 2026)
- ISRO, "India Bags Credit First-Ever In-Situ Measurement": isro.gov.in; Communications Earth and Environment, doi 10.1038/s43247-025-02114-6
- Space Data Atlas (independent, not official): spacedata.swapniltamse.com/challenges/earth-analogs-moon-mars/
- CSA: asc-csa.gc.ca/eng/astronomy/moon-exploration/canadian-utility-rover-on-the-moon.asp; SpaceQ, "Mission Control taps Magellan Aerospace" and "CSA issues lunar utility rover RFP"
- CARN: SpaceNews (spacenews.com/?p=53546); IPY EOI "Polar Planetary Research Network"
- Mistastin: IAC-12 paper A5.3-B3.6, "Lessons Learned from Analogue Missions at the Mistastin Lake Impact Structure"; Western University news, 2011
- Tunnunik Crater: SpaceQ, "Canada's Arctic as a Moon and Mars analog for our astronauts"
- Devon Island Rover Navigation Dataset: asrl.utias.utoronto.ca/datasets/devon-island-rover-navigation
- RADARSAT-1 open data: canada.ca/en/space-agency/news/2019 (1 April 2019); RCM data: data.asc-csa.gc.ca; EODMS: eodms-sgdot.nrcan-rncan.gc.ca
