from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    chunk_index: int
    text: str


def chunk_page(text: str, page_number: int, chunk_size: int = 1200, overlap: int = 180) -> list[TextChunk]:
    clean = " ".join(text.split())
    if not clean:
        return []
    chunks, start, index = [], 0, 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        if end < len(clean):
            boundary = clean.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(TextChunk(page_number, index, clean[start:end]))
        if end == len(clean):
            break
        start, index = max(end - overlap, start + 1), index + 1
    return chunks
