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
import zipfile
import tempfile
import shutil
import sys

from pysword.bible import SwordBible, BlockType, CompressType
from pysword.utils import path_like_to_str


def get_platform_path():
    """
    Returns the default SWORD datapath for the current platform.

    This is useful if you want to search for modules in both the default path
    and some additional paths.
    """

    if sys.platform.startswith(u'win32'):
        return os.path.join(os.getenv(u'APPDATA'), u'Sword')
    elif sys.platform.startswith(u'darwin'):
        return os.path.join(os.getenv(u'HOME'), u'Library', u'Application Support', u'Sword')
    else:  # Linux etc.
        return os.path.join(os.getenv(u'HOME'), u'.sword')


class SwordModules(object):
    """
    Class used to parse module conf-files.
    """
    def __init__(self, paths=None, encoding=None):
        """
        Initialize the SwordModules object.

        :param paths: Path the SWORD datapath or to a zip-file containing a
                      module. Defaults to the platform's expected SWORD
                      datapath. A list of paths may be given. In that case,
                      modules will be loaded from all of the paths, with later
                      paths taking precedence.
        :param encoding: The encoding to use when reading the text.
        """
        self._encoding = encoding

        if paths is None:
            # Based on the platform find the SWORD data path
            self._sword_paths = [get_platform_path()]
        else:
            if not isinstance(paths, list):
                paths = [paths]

            try:
                self._sword_paths = [path_like_to_str(path) for path in paths]
            except TypeError:
                raise TypeError(u'`path` should be a str, PathLike object or an instance of pathlib.Path')

        self._modules = {}
        self._module_paths = {}
        self._temp_folders = []

    def __del__(self):
        """
        Clean up. If we decompressed a zip-file remove the files again.
        """
        for temp_folder in self._temp_folders:
            # TODO: This sometimes fails because it is getting GC'ed before the files in the bible module are closed!
            shutil.rmtree(temp_folder, ignore_errors=True)

    def _parse_conf_file(self, conf_filename, module_folder):
        """
        Parse a module conf file and add the result to module dict

        :param conf_filename: The conf file to parse.
        :param module_folder: The folder the module is in
        """
        # Open configuration file
        try:
            conf_file_lines = []
            if self._encoding is None:
                # No encoding specified try uft-8
                try:
                    with io.open(conf_filename, mode=u'rt', encoding=u'utf-8', errors=u'strict') as conf_file:
                        conf_file_lines = conf_file.readlines()
                except UnicodeDecodeError:
                    # Fallback to iso=8859-1 (latin-1)
                    self._encoding = u'iso-8859-1'
            if self._encoding:
                with io.open(conf_filename, mode=u'rt', encoding=self._encoding, errors=u'strict') as conf_file:
                    conf_file_lines = conf_file.readlines()
        except Exception as e:
            print(u'Exception %s caught while parsing %s\n%s' % (sys.exc_info()[0].__name__, f, e))
            return
        # Start parsing configuration file
        module_conf = dict()
        module_name = u''
        cur_key = u''
        for line in conf_file_lines:
            # Ignore comments
            if line.startswith(u'#'):
                continue
            line = line.strip()
            # Detect start of module configurations. Support multiple module configurations in one file.
            if line.startswith(u'[') and line.endswith(u']'):
                # If a configuration was already parsed, save it.
                if module_name:
                    self._modules[module_name] = module_conf
                    self._module_paths[module_name] = module_folder
                # Set the module name, strip the '[' and ']'
                module_name = line[1:-1]
                module_conf = dict()
                continue
            # Handle configuration line. Try to split the line by '='.
            line_split = line.split(u'=', 1)
            # if a '=' was detected a new configuration key was found
            if len(line_split) > 1:
                cur_key = line_split[0].lower()
                # Join the remaining elements using a '=', this makes it possible to have a '=' in the value part
                module_conf[cur_key] = u'='.join(line_split[1:])
            else:
                if cur_key and line:
                    module_conf[cur_key] += u'\n' + line
        if module_name:
            self._modules[module_name] = module_conf
            self._module_paths[module_name] = module_folder

    def parse_modules(self):
        """
        Based on the datapath given to the constructor parse modules conf-files and return the result

        :return: A dict containing the data read from the conf files.
        """
        for path in self._sword_paths:
            # If path is a zipfile, we extract it to a temp-folder
            if path.endswith(u'.zip'):
                module_folder = tempfile.mkdtemp()
                self._temp_folders.append(module_folder)
                zipped_module = zipfile.ZipFile(path)
                zipped_module.extractall(module_folder)
            else:
                module_folder = path

            conf_folder = os.path.join(module_folder, u'mods.d')

            # Loop over config files and save data in a dict
            for f in os.listdir(conf_folder):
                if f.endswith(u'.conf'):
                    conf_filename = os.path.join(conf_folder, f)
                    self._parse_conf_file(conf_filename, module_folder)

        # Return the modules metadata
        return self._modules

    def get_bible_from_module(self, module_key, cipher=None):
        """
        Return a SwordBible object for the key given.

        :param module_key: The key to use for finding the module.
        :param cipher: Cipher key to use to decrypt module. Overrules any cipher in the module conf
        :return: a SwordBible object for the key given.
        """
        # TODO could replace the try excepts with a simple.get
        bible_module = self._modules[module_key]
        module_path = os.path.join(self._module_paths[module_key], bible_module[u'datapath'])
        module_type = bible_module[u'moddrv'].lower()
        try:
            module_versification = bible_module[u'versification'].lower()
        except KeyError:
            module_versification = u'kjv'
        try:
            module_encoding = bible_module[u'encoding'].lower()
        except KeyError:
            module_encoding = None
        try:
            source_type = bible_module[u'sourcetype']
        except KeyError:
            source_type = None
        try:
            block_type = bible_module[u'blocktype']
        except KeyError:
            block_type = BlockType.BOOK
        try:
            compress_type = bible_module[u'compress_type']
        except KeyError:
            compress_type = CompressType.ZIP
        if cipher:
            cipherkey = cipher
        else:
            try:
                cipherkey = bible_module[u'cipherkey']
            except KeyError:
                cipherkey = None
        return SwordBible(module_path, module_type, module_versification, module_encoding, source_type, block_type,
                          compress_type, cipherkey)
