"""Tests of the reference checker (network calls are replaced by a fake)."""
from verify_refs import check_reference, compare, parse_references

TABLE = """
| ID | Reference | Status | Used for | Level |
|---|---|---|---|---|
| R1 | Paige, D. A. et al. (2010). Diviner Lunar Radiometer observations of cold traps in the Moon's south polar region. *Science* 330, 479-482. doi:10.1126/science.1187726 | verified | x | y |
| R3 | Smith, D. E. et al. (2010). The Lunar Orbiter Laser Altimeter investigation. *SSR* 150. doi:10.1007/s11214-009-9512-y; and Smith, D. E. et al. (2017). Summary of LOLA results. *Icarus* 283. doi:10.1016/j.icarus.2016.06.006 | verified | x | y |
| R9 | Heiken, G. H. (eds.) (1991). *Lunar Sourcebook*. Cambridge University Press. | not verified (book) | x | y |
"""


def crossref(title, family, year, journal="Science"):
    return {"title": [title], "author": [{"family": family}], "issued": {"date-parts": [[year]]}, "container-title": [journal]}


def test_parse_finds_ids_and_dois():
    refs = parse_references(TABLE)
    assert [r["id"] for r in refs] == ["R1", "R3", "R9"]
    assert refs[1]["dois"] == ["10.1007/s11214-009-9512-y", "10.1016/j.icarus.2016.06.006"]
    assert refs[2]["dois"] == []


def test_compare_accepts_a_matching_record():
    citation = TABLE.splitlines()[3]
    rec = crossref("Diviner Lunar Radiometer Observations of Cold Traps in the Moon's South Polar Region", "Paige", 2010)
    assert compare(citation, rec)["match"] is True


def test_compare_rejects_another_paper():
    citation = TABLE.splitlines()[3]
    rec = crossref("Enhanced deep detection of Raman scattered light by wavefront shaping", "Paniagua-Diaz", 2018)
    result = compare(citation, rec)
    assert result["match"] is False
    assert "author" in result["problems"] and "title" in result["problems"]


def test_online_first_year_and_corporate_author_are_notes_not_mismatches():
    citation = "| R51 | OECD and JRC (2008). Handbook on Constructing Composite Indicators: Methodology and User Guide. OECD. doi:10.1787/x |"
    rec = {"title": ["Handbook on Constructing Composite Indicators: Methodology and User Guide"], "issued": {"date-parts": [[2008]]}}
    result = compare(citation, rec)
    assert result["match"] is True and "no personal author in Crossref" in result["notes"]
    citation3 = TABLE.splitlines()[4]
    rec3 = crossref("The Lunar Orbiter Laser Altimeter Investigation", "Smith", 2009)
    result3 = compare(citation3, rec3)
    assert result3["match"] is True and any("year" in n for n in result3["notes"])


def test_a_two_year_gap_is_still_a_mismatch():
    citation = TABLE.splitlines()[3]
    rec = crossref("Diviner Lunar Radiometer observations of cold traps in the Moon's south polar region", "Paige", 2013)
    assert compare(citation, rec)["match"] is False


def test_check_reference_reports_each_doi_and_unresolvable_ones():
    ref = parse_references(TABLE)[1]
    fake = {"10.1007/s11214-009-9512-y": crossref("The Lunar Orbiter Laser Altimeter Investigation on the Lunar Reconnaissance Orbiter Mission", "Smith", 2010)}
    out = check_reference(ref, fetch=lambda doi: fake.get(doi))
    assert out["results"][0]["match"] is True
    assert out["results"][1]["match"] is False and out["results"][1]["problems"] == ["DOI not found"]
    assert out["verdict"] == "mismatch"


def test_reference_without_doi_is_manual():
    ref = parse_references(TABLE)[2]
    assert check_reference(ref, fetch=lambda doi: None)["verdict"] == "no DOI: manual check"


def test_a_datacite_doi_is_read_as_a_record_when_crossref_does_not_know_it():
    """Data DOIs (PANGAEA) are registered at DataCite, not Crossref: a 404 at Crossref is not a wrong DOI."""
    from verify_refs import datacite_record, first_found
    rec = datacite_record({"data": {"attributes": {"creators": [{"familyName": "Obu", "name": "Obu, Jaroslav"}],
                                                   "publicationYear": 2018, "publisher": "PANGAEA",
                                                   "titles": [{"title": "Ground Temperature Map, 2000-2016, Northern Hemisphere Permafrost"}]}}})
    citation = "Obu, J. et al. (2018). Ground temperature map, 2000-2016, Northern Hemisphere permafrost. PANGAEA. doi:10.1594/PANGAEA.888600"
    assert compare(citation, rec)["match"] is True
    fetch = first_found(lambda doi: None, lambda doi: rec)
    assert fetch("10.1594/PANGAEA.888600") is rec
    assert first_found(lambda doi: None, lambda doi: None)("x") is None
