from apps.api.chunking import chunk_page


def test_chunk_page_keeps_page_metadata_and_overlap():
    chunks = chunk_page("word " * 700, page_number=4, chunk_size=100, overlap=20)
    assert len(chunks) > 2
    assert all(chunk.page_number == 4 for chunk in chunks)
    assert chunks[0].chunk_index == 0
    assert chunks[1].text.split()[0] in chunks[0].text
