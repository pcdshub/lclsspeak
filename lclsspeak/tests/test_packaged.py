from .. import packaged


def test_packaged_load():
    for pkg in packaged._packaged_data:
        items = list(pkg.load(use_cache=True))
        assert len(items) > 15  # otherwise we wouldn't list them here
        for item in items:
            print(item)
            assert item.valid


def test_cached_website_load():
    for pkg in packaged._external_data:
        items = list(pkg.load(use_cache=True))
        assert len(items) > 15  # otherwise we wouldn't list them here
        for item in items:
            print(item)
            assert item.valid
