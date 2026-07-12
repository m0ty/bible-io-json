# -*- coding: utf-8 -*-
###############################################################################
# PySword - A native Python reader of the SWORD Project Bible Modules         #
# --------------------------------------------------------------------------- #
# Copyright (c) 2008-2019 Various PySword developers:                         #
# Kenneth Arnold, Joshua Gross, Tomas Groth, Ryan Hiebert, Philip Ridout,     #
# Matthew Wardrop                                                             #
# --------------------------------------------------------------------------- #
# Permission is hereby granted, free of charge, to any person obtaining a     #
# copy of this software and associated documentation files (the "Software"),  #
# to deal in the Software without restriction, including without limitation   #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,    #
# and/or sell copies of the Software, and to permit persons to whom the       #
# Software is furnished to do so, subject to the following conditions:        #
#                                                                             #
# The above copyright notice and this permission notice shall be included     #
# in all copies or substantial portions of the Software.                      #
#                                                                             #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,    #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER      #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER         #
# DEALINGS IN THE SOFTWARE.                                                   #
###############################################################################

import sys

from pysword.canons import canons

PY3 = sys.version_info > (3,)


class BookStructure(object):
    def __init__(self, name, osis_name, preferred_abbreviation, chapter_lengths):
        """
        :param name: Full English name of book
        :param osis_name: Abbreviation of book
        :param preferred_abbreviation: Preferred abbreviation of book
        :param chapter_lengths: List containing the number of verses for each chapter.
        """
        self.name = name
        self.osis_name = osis_name
        self.preferred_abbreviation = preferred_abbreviation
        self.chapter_lengths = chapter_lengths
        self.num_chapters = len(chapter_lengths)

    def __repr__(self):
        return u'Book(%s)' % self.name

    def name_matches(self, name):
        """
        Check if a name matches the name of this book.

        :param name: The name to match
        :return: True if matching else False
        """
        name = name.lower()
        return name in [self.name.lower(), self.osis_name.lower(), self.preferred_abbreviation.lower()]

    def chapter_offset(self, chapter_index):
        """
        Get offset based on chapter

        :param chapter_index: The chapter index to calculate from.
        :return: The calculated offset.
        """
        # Add chapter lengths to this point; plus 1 for every chapter title; plus 1 for book title
        return sum(self.chapter_lengths[:chapter_index]) + (chapter_index + 1) + 1

    def get_indicies(self, chapters=None, verses=None, offset=0):
        """
        Get indicies for given chapter(s) and verse(s).

        :param chapters: Single chapter number or an array of chapter numbers
        :param verses: Single verse number or an array of verse numbers
        :param offset: The offset to used for this book when reading from file.
        :return: An array of indicies.
        """
        if chapters is None:
            chapters = list(range(1, self.num_chapters+1))
        elif isinstance(chapters, int):
            chapters = [chapters]
        if len(chapters) != 1:
            verses = None
        elif isinstance(verses, int):
            verses = [verses]

        refs = []
        for chapter in chapters:
            if chapter > self.num_chapters:
                raise ValueError(u'Book "%s" only have %d chapters.' % (self.name, self.num_chapters))
            if verses is None:
                tmp_verses = list(range(1, self.chapter_lengths[chapter-1]+1))
            else:
                tmp_verses = verses
            if tmp_verses[-1] > self.chapter_lengths[chapter-1]:
                raise ValueError(u'Book "%s", chapter %d, only have %d verses.' %
                                 (self.name, chapter, self.chapter_lengths[chapter-1]))
            refs.extend([offset + self.chapter_offset(chapter-1) + verse-1 for verse in tmp_verses])
        return refs

    @property
    def size(self):
        """
        Size of book.
        """
        # Total verses + chapter heading for each chapter + 1 for book title
        return sum(self.chapter_lengths) + len(self.chapter_lengths) + 1


class BibleStructure(object):

    def __init__(self, versification, testaments=[u'ot', u'nt']):
        """
        Initialize structure based on the versification.

        :param versification: The versification to use.
        :param testaments: List of testaments in this bible, must be 'ot' and/or 'nt'
        """
        self._book_offsets = None  # offsets within sections
        self._books = {}

        # Find the canon used. The canons are original defined in SWORD header files.
        if versification not in canons.keys():
            raise ValueError('The versification "%s" is unknown!' % versification)
        else:
            canon = canons[versification]

        # Based on the canon create the BookStructure objects needed
        for testament in testaments:
            self._books[testament] = []
            for book in canon[testament]:
                self._books[testament].append(BookStructure(*book))

    def _update_book_offsets(self):
        """
        Compute index offsets and add other data
        """
        # FIXME: this is still a little hairy.
        self._book_offsets = {}
        for testament, books in self._books.items():
            idx = 2  # start after the testament heading
            for book in books:
                self._book_offsets[book.name] = idx
                offset = 1  # start after the book heading
                idx += book.size

    def _book_offset(self, book_name):
        """
        Find offset for the given book

        :param book_name: Name of book to find offset for
        :return: The offset
        """
        if self._book_offsets is None:
            self._update_book_offsets()
        return self._book_offsets[book_name]

    def find_book(self, name):
        """
        Find book

        :param name: The book to find
        :return: A tuple of the testament the book is in ('ot' or 'nt') and a BookStructure object.
        :raise ValueError: If the book is not in this BibleStructure.
        """
        name = name.lower()
        for testament, books in self._books.items():
            for num, book in enumerate(books):
                if book.name_matches(name):
                    return testament, book
        raise ValueError(u'Book name "%s" does not exist in BibleStructure.' % name)

    def ref_to_indicies(self, books=None, chapters=None, verses=None):
        """
        Get references to indicies for given book(s), chapter(s) and verse(s).

        :param books: Single book name or an array of book names
        :param chapters: Single chapter number or an array of chapter numbers
        :param verses: Single verse number or an array of verse numbers
        :return:
        """
        # TODO: CHECK NOT OVERSPECIFIED
        if books is None:
            # Return all books
            books = []
            for section in self._books:
                books.extend([b.name for b in self._books[section]])
        # It is needed to check for both str and unicode for python2 support
        elif isinstance(books, str) or not PY3 and isinstance(books, unicode):
            books = [books]

        refs = {}
        for book in books:
            testament, book = self.find_book(book)
            if testament not in refs:
                refs[testament] = []
            refs[testament].extend(book.get_indicies(chapters=chapters, verses=verses,
                                                     offset=self._book_offset(book.name)))
            # Deal with the one book presented.
        return refs

    def get_books(self):
        """
        Return the bookstructure for this bible.

        :return: book structure
        """
        return self._books
