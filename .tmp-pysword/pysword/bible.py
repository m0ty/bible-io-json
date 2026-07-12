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

import io
import os
import struct
import zlib
import bz2
import sys

from pysword.books import BibleStructure
from pysword.cleaner import OSISCleaner, GBFCleaner, ThMLCleaner
from pysword.utils import path_like_to_str
from pysword.sapphire import Sapphire

PY3 = sys.version_info > (3,)

if PY3:
    import lzma


class SwordModuleType:
    RAWTEXT = u'rawtext'
    RAWTEXT4 = u'rawtext4'
    ZTEXT = u'ztext'
    ZTEXT4 = u'ztext4'


class BlockType:
    BOOK = u'BOOK'
    CHAPTER = u'CHAPTER'
    VERSE = u'VERSE'

    @staticmethod
    def get_file_ext_first_letter(block_type):
        """
        Return the first letter of modules file extensions based on the block type.

        :param block_type: Type of block, can be BOOK, CHAPTER or VERSE.
        :return: The first letter of modules file extensions based on the block type.
        """
        if block_type == BlockType.BOOK:
            return u'b'
        elif block_type == BlockType.CHAPTER:
            return u'c'
        elif block_type == BlockType.VERSE:
            return u'v'
        else:
            return u''


class CompressType:
    ZIP = u'ZIP'
    BZIP2 = u'BZIP2'
    XZ = u'XZ'
    LZSS = u'LZSS'


class Testament(object):
    """
    :class:`Testament` manages the file for each testament.
    """

    def __init__(self, testament_name, **kwargs):
        """
        Load the files specified in `kwargs` and keep a handle for the files.

        :param str testament_name: Name of the testament this instance represents.
        :param dict[str] kwargs: A dictionary of files to load.
        """
        self.name = testament_name
        self._open_files = []
        for key, value in kwargs.items():
            file_handle = io.open(value, u'rb')
            setattr(self, key, file_handle)
            self._open_files.append(file_handle)
            # Set a size attribute. Should be named v2b_size, b2l_size, text_size
            size_key = '%s_size' % key.split(u'_')[0]
            setattr(self, size_key, os.fstat(file_handle.fileno()).st_size)

    def __del__(self):
        """
        Ensure that the file open handles are closed when the :class:Testament object is deleted.

        :rtype: None
        """
        for file_handle in self._open_files:
            file_handle.close()


class SwordBible(object):
    """
    :class:`SwordBible` is an abstract base class containing the core common functionality required by each SWORD module
    type.
    """

    def __new__(cls, *args, **kwargs):
        """
        Override the creation of a new instance of this class, instead create an instance of the specific subclass as
        specified by the module_type parameter.

        :param args: The positional arguments that this method was called with.
        :param kwargs: The keyword arguments that this method was called with.
        :return: The subclass required to parse the module specified by the module_type parmeter.
        """
        if cls != SwordBible:
            # The user has chosen the specific Module type the wish to use. Lets assume they know best and go with it
            return super(SwordBible, cls).__new__(cls)
        module_type = None
        if 'module_type' in kwargs:
            module_type = kwargs['module_type']
        elif len(args) >= 2:
            # The module_type parameter was not specified with a keyword and there are two or more positional arguments,
            # so the second positional argument must be the module_type
            module_type = args[1]
        # Validate the module type
        if module_type and module_type not in [SwordModuleType.RAWTEXT, SwordModuleType.RAWTEXT4, SwordModuleType.ZTEXT,
                                               SwordModuleType.ZTEXT4]:
            raise ValueError(u'ModDrv/module_type "%s" is not supported.' % module_type)
        if not module_type:
            module_type = SwordModuleType.ZTEXT
        return super(SwordBible, cls).__new__(SwordBible._MODULE_CLASSES[module_type])

    def __init__(self, module_path, module_type=None, versification=u'kjv', encoding=None, source_type=u'OSIS',
                 block_type=BlockType.BOOK, compress_type=CompressType.ZIP, cipherkey=None):
        """
        Initialize the SwordBible object.

        :param module_path: Path to SWORD modules datapath.
        :param module_type: Types as defined by SwordModuleType, defaults to SwordModuleType.ZText
        :param versification: Versification used for bible, defaults to 'kjv'.
        :param encoding: Encoding used by the bible, should be either 'utf-8' or 'latin1'.
        :param source_type: Type of (possible) tags in the text, can be 'OSIS', 'GBF' or 'ThML'.
        :param block_type: Type of block used for this module, can be BOOK, CHAPTER or VERSE.
        :param compress_type: Type of compression used for this module, can be ZIP, BZIP2, XZ or LZSS.
        :param cipherkey: Cipher to use to decrypt text.
        """
        self._encoding = encoding
        self._block_type = block_type
        self._compress_type = compress_type
        self._setup(module_path, versification, source_type, cipherkey)

    def _setup(self, module_path, versification, source_type, cipherkey):
        """
        Preform setup separate from __init__ to allow easier patching when testing

        :raise IOError: If files cannot be opened.
        :raise ValueError: If unknown module_type is supplied.
        """
        try:
            self._module_path = path_like_to_str(module_path)
        except TypeError:
            raise TypeError(u'`module_path` should be a str, PathLike object or an instance of pathlib.Path')

        self._testaments = {}
        self._load_testament('ot')
        self._load_testament('nt')
        if not self._testaments:
            raise IOError(u'Could not open OT or NT for module')

        # Create cleaner to remove OSIS or GBF tags
        if source_type:
            if source_type.upper() == u'THML':
                self._cleaner = ThMLCleaner()
            elif source_type.upper() == u'GBF':
                self._cleaner = GBFCleaner()
            else:
                self._cleaner = OSISCleaner()
        else:
            self._cleaner = OSISCleaner()
        self._structure = BibleStructure(versification, self._testaments)

        # Initialise decryption if needed
        if cipherkey:
            self._sappire_decryptor = Sapphire(cipherkey)
        else:
            self._sappire_decryptor = None

    def _decode_bytes(self, byte_data):
        """
        Decode the param:`byte_data`. If instance variable :ivar:`_encoding` has been set use that exclusively.
        Otherwise assume utf-8. If that fails set :ivar:`_encoding` so that the rest of the document is decoded as
        cp1252 (a superset of latin-1/iso-8859-1)

        :param byte_data: The data to decode. str in Py2, bytes in Py3
        :return: The decoded data. unicode in Py2, str in Py3
        """
        if not self._encoding:
            # No encoding specified try utf-8
            try:
                unicode_data = byte_data.decode(u'utf-8', u'strict')
            except UnicodeDecodeError as u:
                # Fallback to decoding the rest of the document as cp1252 (a superset of latin-1/iso-8859-1)
                self._encoding = u'cp1252'
        if self._encoding:
            unicode_data = byte_data.decode(self._encoding, u'replace')
        return unicode_data

    def _load_testament(self, testament_name):
        """
        `_load_testament` needs to be reimplemented in the specific module subclass.

        :param testament_name: The name of the testament to be loaded.
        :rtype: None
        """
        raise NotImplemented('`_load_testament` needs to be overridden')

    # USER FACING #################################################################################
    def get_iter(self, books=None, chapters=None, verses=None, clean=True):
        """
        Retrieve the text for a given reference as a dict.

        :param books: Single book name or an array of book names
        :param chapters: Single chapter number or an array of chapter numbers
        :param verses: Single verse number or an array of verse numbers
        :param clean: True for cleaning text for tags, False to keep them.
        :return: iterator for the dict that contains the text
        """
        indicies = self._structure.ref_to_indicies(books=books, chapters=chapters, verses=verses)

        for testament, idxs in indicies.items():
            for idx in idxs:
                text = self._text_for_index(testament, idx)
                if text is None:
                    continue
                if clean and self._cleaner and '<' in text:
                    text = self._cleaner.clean(text)
                yield text

    def get(self, books=None, chapters=None, verses=None, clean=True, join='\n'):
        """
        Retrieve the text for a given reference.

        :param books: Single book name or an array of book names
        :param chapters: Single chapter number or an array of chapter numbers
        :param verses: Single verse number or an array of verse numbers
        :param clean: True for cleaning text for tags, False to keep them.
        :param join: The char/string that should be used to mark a new verse, defaults to newline
        :return: the text for the reference.
        """
        output = []
        output.extend(list(self.get_iter(books=books, chapters=chapters, verses=verses, clean=clean)))
        return join.join(output)

    def get_structure(self):
        """
        Retrieve the structure of this bible.
        :return: BibleStructure of this bible
        """
        return self._structure


class RawTextModule(SwordBible):
    """
    :class:`RawTextModule` subclasses :class:`SwordBible` allowing the RawText version of SWORD bibles to be parsed.
    """

    def __init__(self, *args, **kwargs):
        """
        Initalise the instance, setting some specific instance variables for parsing raw text SWORD bibles.

        :param args: Positional arguments to pass on to the super class.
        :param kwargs: Keyword arguments to pass on to the super class.
        """
        super(RawTextModule, self).__init__(*args, **kwargs)
        self._verse_record_format = '<IH'
        self._verse_record_size = 6

    def _load_testament(self, testament_name):
        """
        Load the testaments according to the files used in the raw text SWORD bible.

        :param str testament_name: The name of the testament the files represent
        :rtype: None
        """
        base_file_path = os.path.join(self._module_path, u'%s%s')
        try:
            testament = Testament(testament_name,
                                  v2l_name=base_file_path % (testament_name, u'.vss'),
                                  text_name=base_file_path % (testament_name, u'')
                                  )
            self._testaments[testament_name] = testament
        except IOError:
            # Ignore IOErrors, if one occurs, the Testament object will not be saved in the :ivar:`_testaments`
            pass

    def _text_for_index(self, testament, index):
        """
        Get the rawtext for a given index.

        :param str testament: 'ot' or 'nt'
        :param int index: Verse buffer to read
        :return: the text.
        :rtype: str
        """
        # Verify that the data is available
        if (self._verse_record_size * (index + 1)) > self._testaments[testament].v2l_size:
            return u''

        verse_to_loc = self._testaments[testament].v2l_name
        text = self._testaments[testament].text_name

        # Read the verse record.
        verse_to_loc.seek(self._verse_record_size * index)
        verse_start, verse_len = struct.unpack(self._verse_record_format, verse_to_loc.read(self._verse_record_size))

        # Verify that the data is available
        if (verse_start + verse_len) > self._testaments[testament].text_size:
            return b''

        text.seek(verse_start)
        ret_text = text.read(verse_len)

        # Decrypt if neccesary
        if self._sappire_decryptor:
            ret_text = self._sappire_decryptor.decrypt_bytes(ret_text)

        return self._decode_bytes(ret_text)


class RawTextModule4(RawTextModule):
    """
    Subclass the :class:`RawTextModule` to allow parsing SWORD bibles that use the Raw Text Specification.
    """

    def __init__(self, *args, **kwargs):
        """
        Initalise the instance, setting some specific instance variables for parsing raw text SWORD bibles.

        :param args: Positional arguments to pass on to the super class.
        :param kwargs: Keyword arguments to pass on to the super class.
        """
        super(RawTextModule4, self).__init__(*args, **kwargs)
        self._verse_record_format = '<II'
        self._verse_record_size = 8


class ZTextModule(SwordBible):
    def __init__(self, *args, **kwargs):
        """
        Initalise the instance, setting some specific instance variables for parsing raw text SWORD bibles.

        :param args: Positional arguments to pass on to the super class.
        :param kwargs: Keyword arguments to pass on to the super class.
        """
        super(ZTextModule, self).__init__(*args, **kwargs)
        self._verse_record_format = '<IIH'
        self._verse_record_size = 10

    def _load_testament(self, testament_name):
        """
        Load the testaments according to the files used in the zipped text SWORD bible.

        :param str testament_name: The name of the testament the files represent
        :rtype: None
        """
        file_ext_first = BlockType.get_file_ext_first_letter(self._block_type)
        base_file_path = os.path.join(self._module_path, u'%s.%sz%s')
        try:
            testament = Testament(testament_name,
                                  v2b_name=base_file_path % (testament_name, file_ext_first, u'v'),
                                  b2l_name=base_file_path % (testament_name, file_ext_first, u's'),
                                  text_name=base_file_path % (testament_name, file_ext_first, u'z')
                                  )
            self._testaments[testament_name] = testament
        except IOError:
            # Ignore IOErrors, if one occurs, the Testament object will not be saved in the :ivar:`_testaments`
            pass

    def _text_for_index(self, testament, index):
        """
        Get the ztext for a given index.

        :param testament: 'ot' or 'nt'
        :param index: Verse buffer to read
        :return: the text.
        """
        # Verify that the data is available
        if (self._verse_record_size * (index + 1)) > self._testaments[testament].v2b_size:
            return u''

        verse_to_buf = self._testaments[testament].v2b_name

        # Read the verse record.
        verse_to_buf.seek(self._verse_record_size * index)
        buf_num, verse_start, verse_len = struct.unpack(self._verse_record_format,
                                                        verse_to_buf.read(self._verse_record_size))
        decompressed_text = self._decompressed_text(testament, buf_num)
        return self._decode_bytes(decompressed_text[verse_start:verse_start + verse_len])

    def _decompressed_text(self, testament, buf_num):
        """
        Decompress ztext at given position.

        :param testament: 'ot' or 'nt'
        :param buf_num: Buffer to read
        :return: The decompressed text
        """
        # Verify that the data is available
        if ((buf_num + 1) * 12) > self._testaments[testament].b2l_size:
            return b''

        buf_to_loc = self._testaments[testament].b2l_name
        text = self._testaments[testament].text_name

        # Determine where the compressed data starts and ends.
        buf_to_loc.seek(buf_num * 12)
        offset, size, uc_size = struct.unpack('<III', buf_to_loc.read(12))

        # Verify that the data is available
        if (offset + size) > self._testaments[testament].text_size:
            return b''

        # Get the compressed data.
        text.seek(offset)
        compressed_data = text.read(size)

        # Decrypt if neccesary
        if self._sappire_decryptor:
            compressed_data = self._sappire_decryptor.decrypt_bytes(compressed_data)

        # Decompress
        decompressed_data = self._decompress(compressed_data)
        return decompressed_data

    def _decompress(self, compressed_data):
        """
        Decompress data using algorithm the modules uses

        :param data: The to decompress
        :return: The decompressed text
        """
        decompressed_data = b''
        if self._compress_type == CompressType.ZIP:
            try:
                decompressed_data = zlib.decompress(compressed_data)
            except zlib.error:
                decompressed_data = b''
        elif self._compress_type == CompressType.BZIP2:
            try:
                decompressed_data = bz2.decompress(compressed_data)
            except Exception:
                decompressed_data = b''
        elif self._compress_type == CompressType.XZ:
            if PY3:
                try:
                    decompressed_data = lzma.decompress(compressed_data)
                except Exception:
                    decompressed_data = b''
            else:
                raise NotImplementedError(u'XZ compressed modules is not supported under python2')
        elif self._compress_type == CompressType.LZSS:
            raise NotImplementedError(u'LZSS compressed modules is not yet supported')
        return decompressed_data


class ZTextModule4(ZTextModule):
    def __init__(self, *args, **kwargs):
        """
        Initalise the instance, setting some specific instance variables for parsing raw text SWORD bibles.

        :param args: Positional arguments to pass on to the super class.
        :param kwargs: Keyword arguments to pass on to the super class.
        """
        super(ZTextModule4, self).__init__(*args, **kwargs)
        self._verse_record_format = '<III'
        self._verse_record_size = 12


# Set this here, rather than in the SwordBible class, as the module cannot set these before the classes have been
# defined, but the classes cannot be defined until the SwordBible class has been created (they subclass it)
SwordBible._MODULE_CLASSES = {SwordModuleType.RAWTEXT: RawTextModule, SwordModuleType.RAWTEXT4: RawTextModule4,
                              SwordModuleType.ZTEXT: ZTextModule, SwordModuleType.ZTEXT4: ZTextModule4}
