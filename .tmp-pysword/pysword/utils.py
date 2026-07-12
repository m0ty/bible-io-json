# -*- coding: utf-8 -*-
###############################################################################
# PySword - A native Python reader of the SWORD Project Bible Modules         #
# --------------------------------------------------------------------------- #
# Copyright (c) 2008-2019 Various Pysword developers:                         #
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

import os
import sys
try:
    import pathlib
    pathlib_available = True
except ImportError:
    pathlib_available = False

PY3 = sys.version_info > (3,)


def path_like_to_str(path):
    """
    Take an object and convert it to a string representation of a file path.

    :param path: The object to convert, should be an `os.PathLike` object, a `pathlib.Path` object or a str object
    :return: The string representation of the path
    """
    if PY3:
        if isinstance(path, str):
            return path
        if hasattr(path, '__fspath__'):
            # py 3.6 and above implemented os.PathLike objects, which make use if the __fspath__ method.
            return os.fspath(path)
        if pathlib_available and isinstance(path, pathlib.Path):
            # py 3.4 and 3.5 have the pathlib.Path object, but it doesn't have the fspath interface.
            return str(path)
    else:
        if isinstance(path, unicode):
            return path
    raise TypeError
