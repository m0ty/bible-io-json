import json
import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_FILE = PROJECT_ROOT / "English" / "eng-kjv-1769.json"
JSON_FILES = sorted(PROJECT_ROOT.glob("*/*.json"))
CRAWLER_REFERENCE_PATTERN = re.compile(r"\[ \([^)]+ \d+:\d+\)")


def _load_json(file_path: Path) -> object:
    try:
        with file_path.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        pytest.fail(f"Could not load {file_path}: {error}")


@pytest.fixture(scope="session")
def canonical_chapters_by_book() -> dict[str, frozenset[str]]:
    """Load the canonical book and chapter keys without assuming verse counts."""
    data = _load_json(CANONICAL_FILE)
    assert isinstance(data, dict), (
        f"Top-level JSON value is not an object in {CANONICAL_FILE}"
    )

    books = data.get("books")
    assert isinstance(books, dict), (
        f"'books' is not an object in {CANONICAL_FILE}"
    )
    assert books, f"'books' is empty in {CANONICAL_FILE}"

    result: dict[str, frozenset[str]] = {}
    for book_key, book_data in books.items():
        assert isinstance(book_key, str) and book_key, (
            f"Book key must be a nonempty string in {CANONICAL_FILE}"
        )
        assert isinstance(book_data, dict), (
            f"Book '{book_key}' is not an object in {CANONICAL_FILE}"
        )

        chapters = book_data.get("chapters")
        assert isinstance(chapters, dict), (
            f"'chapters' is not an object in book '{book_key}' "
            f"in {CANONICAL_FILE}"
        )
        assert chapters, (
            f"Book '{book_key}' contains no chapters in {CANONICAL_FILE}"
        )
        assert all(
            isinstance(chapter_key, str) and chapter_key.isdigit()
            for chapter_key in chapters
        ), f"Book '{book_key}' has a nonnumeric chapter key in {CANONICAL_FILE}"

        result[book_key] = frozenset(chapters)

    return result


def test_bible_json_corpus_is_not_empty() -> None:
    assert JSON_FILES, "No Bible JSON files were discovered"


@pytest.mark.parametrize("file_path", JSON_FILES, ids=lambda path: path.stem)
def test_bible_json_structure(
    file_path: Path,
    canonical_chapters_by_book: dict[str, frozenset[str]],
) -> None:
    """Every bundled Bible must have complete, nonblank structural content."""
    data = _load_json(file_path)

    assert isinstance(data, dict), (
        f"Top-level JSON value is not an object in {file_path}"
    )

    for field in ("id", "name", "description", "language"):
        assert field in data, f"Missing '{field}' in {file_path}"
        assert isinstance(data[field], str), f"'{field}' is not a string in {file_path}"
        assert data[field].strip(), f"'{field}' is blank in {file_path}"

    assert data["id"] == file_path.stem, (
        f"Bible id '{data['id']}' does not match filename '{file_path.stem}'"
    )
    assert "books" in data, f"Missing 'books' in {file_path}"
    books = data["books"]
    assert isinstance(books, dict), f"'books' is not an object in {file_path}"
    assert books, f"'books' is empty in {file_path}"

    canonical_books = set(canonical_chapters_by_book)
    file_books = set(books)
    assert file_books == canonical_books, (
        f"Book abbreviations mismatch in {file_path}:\n"
        f"Missing: {sorted(canonical_books - file_books)}\n"
        f"Extra: {sorted(file_books - canonical_books)}"
    )

    for book_key, book_data in books.items():
        assert isinstance(book_key, str) and book_key, (
            f"Book key must be a nonempty string in {file_path}"
        )
        assert isinstance(book_data, dict), (
            f"Book '{book_key}' is not an object in {file_path}"
        )
        assert "name" in book_data, (
            f"Missing 'name' in book '{book_key}' in {file_path}"
        )
        assert isinstance(book_data["name"], str), (
            f"'name' is not a string in book '{book_key}' in {file_path}"
        )
        assert book_data["name"].strip(), (
            f"'name' is blank in book '{book_key}' in {file_path}"
        )
        assert "chapters" in book_data, (
            f"Missing 'chapters' in book '{book_key}' in {file_path}"
        )
        assert isinstance(book_data["chapters"], dict), (
            f"'chapters' is not an object in book '{book_key}' in {file_path}"
        )
        assert book_data["chapters"], (
            f"Book '{book_key}' contains no chapters in {file_path}"
        )

        canonical_chapters = canonical_chapters_by_book[book_key]
        file_chapters = set(book_data["chapters"])
        assert file_chapters == canonical_chapters, (
            f"Chapter keys mismatch in book '{book_key}' in {file_path}:\n"
            f"Missing: {sorted(canonical_chapters - file_chapters)}\n"
            f"Extra: {sorted(file_chapters - canonical_chapters)}"
        )

        for chapter_key, chapter_data in book_data["chapters"].items():
            assert isinstance(chapter_key, str) and chapter_key.isdigit(), (
                f"Chapter key '{chapter_key}' is not numeric in book '{book_key}' "
                f"in {file_path}"
            )
            assert isinstance(chapter_data, dict), (
                f"Chapter '{chapter_key}' is not an object in book '{book_key}' "
                f"in {file_path}"
            )
            assert chapter_data, (
                f"Chapter '{chapter_key}' contains no verses in book '{book_key}' "
                f"in {file_path}"
            )

            verse_keys = set(chapter_data)
            assert all(
                isinstance(verse_key, str) and verse_key.isdigit()
                for verse_key in verse_keys
            ), (
                f"Chapter '{chapter_key}' of book '{book_key}' has a "
                f"nonnumeric verse key in {file_path}"
            )
            expected_verse_keys = {
                str(number) for number in range(1, len(chapter_data) + 1)
            }
            assert verse_keys == expected_verse_keys, (
                f"Verse keys are not contiguous in chapter '{chapter_key}' of "
                f"book '{book_key}' in {file_path}:\n"
                f"Missing: {sorted(expected_verse_keys - verse_keys)}\n"
                f"Extra: {sorted(verse_keys - expected_verse_keys)}"
            )

            for verse_key, verse_text in chapter_data.items():
                assert isinstance(verse_text, str), (
                    f"Verse '{verse_key}' is not a string in chapter "
                    f"'{chapter_key}' of book '{book_key}' in {file_path}"
                )
                assert verse_text.strip(), (
                    f"Verse '{verse_key}' is blank in chapter '{chapter_key}' "
                    f"of book '{book_key}' in {file_path}"
                )


@pytest.mark.parametrize(
    "relative_path",
    [
        "Chinese/zho-ncv-trad-shen.json",
        "Korean/kor-krv-1938.json",
    ],
)
def test_repaired_translations_have_31104_populated_verses(
    relative_path: str,
) -> None:
    """Catch translation-wide truncation, not only the originally empty chapters."""
    file_path = PROJECT_ROOT / relative_path
    data = _load_json(file_path)
    assert isinstance(data, dict), f"Top-level value is not an object in {file_path}"

    books = data.get("books")
    assert isinstance(books, dict), f"'books' is not an object in {file_path}"

    verse_texts: list[object] = []
    for book_key, book_data in books.items():
        assert isinstance(book_data, dict), (
            f"Book '{book_key}' is not an object in {file_path}"
        )
        chapters = book_data.get("chapters")
        assert isinstance(chapters, dict), (
            f"'chapters' is not an object in book '{book_key}' in {file_path}"
        )

        for chapter_key, chapter_data in chapters.items():
            assert isinstance(chapter_data, dict), (
                f"Chapter '{chapter_key}' is not an object in book "
                f"'{book_key}' in {file_path}"
            )
            verse_texts.extend(chapter_data.values())

    populated_verse_count = sum(
        isinstance(verse_text, str) and bool(verse_text.strip())
        for verse_text in verse_texts
    )
    assert len(verse_texts) == 31_104, (
        f"Expected 31,104 verse entries in {file_path}, found {len(verse_texts):,}"
    )
    assert populated_verse_count == 31_104, (
        f"Expected 31,104 populated verses in {file_path}, "
        f"found {populated_verse_count:,}"
    )


def test_korean_translation_has_no_crawler_reference_artifacts() -> None:
    """Reject verses produced by concatenating subsequent crawler records."""
    file_path = PROJECT_ROOT / "Korean" / "kor-krv-1938.json"
    data = _load_json(file_path)
    assert isinstance(data, dict), f"Top-level value is not an object in {file_path}"

    books = data.get("books")
    assert isinstance(books, dict), f"'books' is not an object in {file_path}"

    artifact_locations: list[str] = []
    for book_key, book_data in books.items():
        assert isinstance(book_data, dict), (
            f"Book '{book_key}' is not an object in {file_path}"
        )
        chapters = book_data.get("chapters")
        assert isinstance(chapters, dict), (
            f"'chapters' is not an object in book '{book_key}' in {file_path}"
        )

        for chapter_key, chapter_data in chapters.items():
            assert isinstance(chapter_data, dict), (
                f"Chapter '{chapter_key}' is not an object in book "
                f"'{book_key}' in {file_path}"
            )
            for verse_key, verse_text in chapter_data.items():
                assert isinstance(verse_text, str), (
                    f"Verse '{verse_key}' is not a string in chapter "
                    f"'{chapter_key}' of book '{book_key}' in {file_path}"
                )
                if CRAWLER_REFERENCE_PATTERN.search(verse_text):
                    artifact_locations.append(
                        f"{book_key} {chapter_key}:{verse_key}"
                    )

    assert not artifact_locations, (
        f"Crawler merged-reference artifacts remain in {file_path}: "
        f"{', '.join(artifact_locations)}"
    )


@pytest.mark.parametrize(
    ("relative_path", "book_key", "expected_counts"),
    [
        (
            "Chinese/zho-ncv-trad-shen.json",
            "so",
            {
                "1": 17,
                "2": 17,
                "3": 11,
                "4": 16,
                "5": 16,
                "6": 13,
                "7": 13,
                "8": 14,
            },
        ),
        (
            "Korean/kor-krv-1938.json",
            "job",
            {
                "35": 16,
                "36": 33,
                "37": 24,
                "38": 41,
                "39": 30,
                "40": 24,
                "41": 34,
                "42": 17,
            },
        ),
        (
            "Korean/kor-krv-1938.json",
            "1pe",
            {"2": 25, "3": 22, "4": 19, "5": 14},
        ),
    ],
)
def test_repaired_source_chapter_verse_counts(
    relative_path: str,
    book_key: str,
    expected_counts: dict[str, int],
) -> None:
    """Guard source ranges that were empty or shifted by merged verses."""
    file_path = PROJECT_ROOT / relative_path
    data = _load_json(file_path)
    assert isinstance(data, dict), f"Top-level value is not an object in {file_path}"

    books = data.get("books")
    assert isinstance(books, dict), f"'books' is not an object in {file_path}"

    book_data = books.get(book_key)
    assert isinstance(book_data, dict), (
        f"Book '{book_key}' is not an object in {file_path}"
    )
    chapters = book_data.get("chapters")
    assert isinstance(chapters, dict), (
        f"'chapters' is not an object in book '{book_key}' in {file_path}"
    )

    actual_counts: dict[str, int] = {}
    for chapter_key in expected_counts:
        chapter_data = chapters.get(chapter_key)
        assert isinstance(chapter_data, dict), (
            f"Chapter '{chapter_key}' is not an object in book '{book_key}' "
            f"in {file_path}"
        )
        actual_counts[chapter_key] = len(chapter_data)

    assert actual_counts == expected_counts
