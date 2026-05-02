import json
import glob
import os
import pytest

# Collect all JSON files
json_files = glob.glob("*/**/*.json", recursive=True)

@pytest.mark.parametrize("file_path", json_files)
def test_bible_json_structure(file_path):
    """Test that each Bible JSON file has the correct basic structure and matching book abbreviations."""
    # Load the canonical Bible (English KJV) to get the standard book abbreviations
    canonical_file = "English/eng-kjv-1769.json"
    with open(canonical_file, 'r', encoding='utf-8') as f:
        canonical_data = json.load(f)
    canonical_books = set(canonical_data["books"].keys())
    
    print(f"\nTesting Bible version: {os.path.basename(file_path)}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"  ID: {data['id']}")
    print(f"  Name: {data['name']}")
    print(f"  Language: {data['language']}")
    print(f"  Description: {data['description']}")
    print(f"  Number of books: {len(data['books'])}")
    
    # Check that book abbreviations match the canonical set
    file_books = set(data["books"].keys())
    if file_books != canonical_books:
        missing = canonical_books - file_books
        extra = file_books - canonical_books
        error_msg = f"Book abbreviations mismatch in {file_path}:\nMissing: {sorted(missing)}\nExtra: {sorted(extra)}"
        assert False, error_msg
    
    # Check top-level keys
    assert "id" in data, f"Missing 'id' in {file_path}"
    assert isinstance(data["id"], str), f"'id' is not a string in {file_path}"
    
    assert "name" in data, f"Missing 'name' in {file_path}"
    assert isinstance(data["name"], str), f"'name' is not a string in {file_path}"
    
    assert "description" in data, f"Missing 'description' in {file_path}"
    assert isinstance(data["description"], str), f"'description' is not a string in {file_path}"
    
    assert "language" in data, f"Missing 'language' in {file_path}"
    assert isinstance(data["language"], str), f"'language' is not a string in {file_path}"
    
    assert "books" in data, f"Missing 'books' in {file_path}"
    assert isinstance(data["books"], dict), f"'books' is not a dict in {file_path}"
    
    # Check each book
    for book_key, book_data in data["books"].items():
        print(f"    Book: {book_key} - {book_data['name']}")
        assert isinstance(book_key, str), f"Book key '{book_key}' is not a string in {file_path}"
        assert len(book_key) > 0, f"Book key is empty in {file_path}"
        
        assert "chapters" in book_data, f"Missing 'chapters' in book '{book_key}' in {file_path}"
        assert isinstance(book_data["chapters"], dict), f"'chapters' is not a dict in book '{book_key}' in {file_path}"
        
        assert "name" in book_data, f"Missing 'name' in book '{book_key}' in {file_path}"
        assert isinstance(book_data["name"], str), f"'name' is not a string in book '{book_key}' in {file_path}"
        
        print(f"      Chapters: {len(book_data['chapters'])}")
        
        # Check each chapter
        for chapter_key, chapter_data in book_data["chapters"].items():
            assert chapter_key.isdigit(), f"Chapter key '{chapter_key}' is not a digit string in book '{book_key}' in {file_path}"
            assert isinstance(chapter_data, dict), f"Chapter '{chapter_key}' is not a dict in book '{book_key}' in {file_path}"
            
            # Check each verse
            for verse_key, verse_text in chapter_data.items():
                assert verse_key.isdigit(), f"Verse key '{verse_key}' is not a digit string in chapter '{chapter_key}' of book '{book_key}' in {file_path}"
                assert isinstance(verse_text, str), f"Verse '{verse_key}' is not a string in chapter '{chapter_key}' of book '{book_key}' in {file_path}"