from .. import slacspeak


def test_parse():
    definitions = slacspeak.get_packaged_slacspeak()
    assert len(definitions)

    name_to_defn = {defn.name: defn for defn in definitions}
    zevatron = name_to_defn['Zevatron']
    assert zevatron.definition == 'Hypothetical, highly exotic source capable of accelerating particles to 1 ZeV.'
    assert "slacspeak" in zevatron.tags

    bsl = name_to_defn['BSL']
    assert bsl.definition == 'BioSafety Level'

    last = None
    for name, defn in name_to_defn.items():
        if name not in ("SPEAR", ):
            assert len(defn.definition) < 1000, f"{name} or {last} may have malformed html"
        last = name

    bsl1 = name_to_defn['BSL-1']
    assert bsl1.definition == 'BioSafety Level 1, a basic level of containment defined by the CDC that relies on standard microbiological practices.'
