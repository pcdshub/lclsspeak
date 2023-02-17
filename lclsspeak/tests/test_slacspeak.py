from .. import slacspeak


def test_parse():
    definitions = slacspeak.get_packaged_slacspeak()
    assert len(definitions)
    
    name_to_defn = {defn.name: defn for defn in definitions}
    zfs = name_to_defn['ZFS']
    assert zfs.definition == 'Hypothetical, highly exotic source capable of accelerating particles to 1 ZeV.'
    assert "slacspeak" in zfs.tags
