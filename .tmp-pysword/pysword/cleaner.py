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

import re


class Cleaner(object):
    def __init(self):
        pass

    def clean(self, text):
        pass


class OSISCleaner(Cleaner):
    """
    Class to clean text of OSIS tags. OSIS spec can be found here: http://www.bibletechnologies.net/
    """
    def __init__(self):
        self.__setup()

    def __setup(self):
        """
        Compile regular expressions that will be used to remove OSIS tags.
        Not all OSIS tags are "mentioned" here since we should only have to deal with those that
        can be found in the biblical texts.
        """
        remove_content_tagnames = [r'note', r'milestone', r'title', r'abbr', r'catchWord', r'index', r'rdg',
                                   r'rdgGroup', r'figure']
        self.__remove_tags_regexes = []
        for tag_name in remove_content_tagnames:
            tag_regex = r'<' + tag_name + r'.*?' + tag_name + r'>'
            self.__remove_tags_regexes.append(re.compile(tag_regex, re.IGNORECASE))
            single_tag_regex = r'<' + tag_name + r'[^<]*/>'
            self.__remove_tags_regexes.append(re.compile(single_tag_regex, re.IGNORECASE))

        keep_content_tagnames = [r'p', r'l', r'lg', r'q', r'a', r'w', r'divineName', r'foreign', r'hi', r'inscription',
                                 r'mentioned', r'name', r'reference', r'seg', r'transChange', r'salute', r'signed',
                                 r'closer', r'speech', r'speaker', r'list', r'item', r'table', r'head', r'row', r'cell',
                                 r'caption', r'chapter', r'div']
        for tag_name in keep_content_tagnames:
            begin_tag_regex = r'<' + tag_name + r'.*?>'
            self.__remove_tags_regexes.append(re.compile(begin_tag_regex, re.IGNORECASE))
            end_tag_regex = r'</' + tag_name + r'>'
            self.__remove_tags_regexes.append(re.compile(end_tag_regex, re.IGNORECASE))
            # Just remove if tag appear in single form
            single_tag_regex = r'<' + tag_name + r'[^<]*/>'
            self.__remove_tags_regexes.append(re.compile(single_tag_regex, re.IGNORECASE))

    def clean(self, text):
        """
        Clean text for OSIS tags.

        :param text: The text to be cleaned
        :return: The cleaned text is returned
        """
        text = re.sub(r'(<[^\>]+type="x-br"[^\>]+\>)', r'\1 ', text)
        for regex in self.__remove_tags_regexes:
            text = regex.sub(u'', text)
        return text


class GBFCleaner(Cleaner):
    """
    Class to clean text of GBF tags. GBF spec can be found here: http://ebible.org/bible/gbf.htm
    """
    def __init__(self):
        self.__setup()

    def __setup(self):
        """
        Compile regular expressions that will be used to remove GBF 'tags'.
        Not all GBF tags are "mentioned" here since we should only have to deal with those that
        can be found in the biblical texts.
        """

        remove_content_tags = [r'<TB>.*?<Tb>', r'<TC>.*?<Tc>', r'<TH>.*?<Th>', r'<TS>.*?<Ts>', r'<TT>.*?<Tt>',
                               r'<TN>.*?<Tn>', r'<TA>.*?<Ta>', r'<TP>.*?<Tp>',
                               r'<FB>.*?<fb>', r'<FC>.*?<fc>', r'<FI>.*?<fi>', r'<FN.*?>.*?<fn>', r'<FO>.*?<fo>',
                               r'<FR>.*?<fr>', r'<FS>.*?<fs>', r'<FU>.*?<fu>', r'<FV>.*?<fv>',
                               r'<RF>.*?<Rf>', r'<RB>', r'<RP.*?>', r'<Rp.*?>', r'<RX.*?>', r'<Rx.*?>',
                               r'<H.*?>',
                               r'<B.*?>',
                               r'<ZZ>',
                               r'<D.*?>', r'<J.*?>', r'<P.>',
                               r'<W.*?>',
                               r'<S.*?>',
                               r'<N.*?>',
                               r'<C.>']
        self.__remove_content_regexes = []
        for tag in remove_content_tags:
            self.__remove_content_regexes.append(re.compile(tag))

    def clean(self, text):
        """
        Clean text for GBF tags.

        :param text: The text to be cleaned
        :return: The cleaned text is returned
        """
        for regex in self.__remove_content_regexes:
            text = regex.sub(u'', text)
        # TODO: Support special char tags <CAxx> and <CUxxxx>
        return text


class ThMLCleaner(Cleaner):
    """
    Class to clean text of ThML tags. ThML spec can be found here: https://www.ccel.org/ThML/
    """
    def __init__(self):
        self.__setup()

    def __setup(self):
        """
        Compile regular expressions that will be used to remove ThML tags.
        Not all ThML tags are "mentioned" here since we should only have to deal with those that
        can be found in the biblical texts.
        """

        remove_content_tags = [r'<scripRef.*?>.*?</scripRef>', r'<scripCom.*?>.*?</scripCom>', r'<.*?>']
        self.__remove_content_regexes = []
        for tag in remove_content_tags:
            self.__remove_content_regexes.append(re.compile(tag))

    def clean(self, text):
        """
        Clean text for ThML tags.

        :param text: The text to be cleaned
        :return: The cleaned text is returned
        """
        for regex in self.__remove_content_regexes:
            text = regex.sub(u'', text)
        return text
