#!/usr/binenv python
#coding: utf-8

import re
import numpy as np
import logging
import sys
import os
import shelve
from collections import defaultdict
from operator import itemgetter
from random import random
from LangModel import LangModel
from string import punctuation
from pprint import pformat
from math import pow


STRIP_REGEX = re.compile('[%s]' % re.escape(punctuation))
LINKS_RE = re.compile("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)")
WIKI_Q_FILE_PATH = 'WikiQsEng/WikiQsEng.txt'
SHELVE_FILE_PATH = 'wiki_q_score.shelve'

class Segmenter(object):
    '''
    Implements Tweet segmenter
    '''

    def __init__(self, U=5, E=5):
        '''
        U : Max length of a segment (default 5)
        E : Max sub segments of a segment to be considered (default 5)
        '''
        self.U = U
        self.E = E

        self.setup_logger()
        if not os.path.exists(SHELVE_FILE_PATH):
            self.wiki_q_hash = self.load_wiki_q(WIKI_Q_FILE_PATH)
            shelve_h = shelve.open(SHELVE_FILE_PATH)
            shelve_h['WIKI_Q'] = self.wiki_q_hash
            shelve_h.close()
        else:
            self.wiki_q_hash = shelve.open(SHELVE_FILE_PATH, flag='r')['WIKI_Q']
        self.cache = {}

    def setup_logger(self):
        self.logger = logging.getLogger("Segmenter")
        handler = logging.FileHandler('Segmenter.log')
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        #self.stdout_handler = logging.StreamHandler(sys.stdout)
        #self.logger.addHandler(self.stdout_handler)

    def load_wiki_q(self, file_path):
        d = {}
        with open(file_path) as f:
            for line in f:
                kwd, p = line.strip().rsplit(',', 1)
                v = max(float(p), float(0))
                if v > 0:
                    kwd = kwd.replace('_', ' ')
                    kwd = STRIP_REGEX.sub(' ', kwd)
                    d[kwd] = v
        return d

    def find_ngrams(self, in_toks, n):
          return zip(*[in_toks[i:] for i in range(n)])

    def find_all_grams(self, in_toks):
        all_grams = []
        for i in xrange(1, self.U+1):
            all_grams.extend([' '.join(each) for each in self.find_ngrams(in_toks, i)])
        return all_grams

    def split_to_words(self, in_str):
        in_str = in_str.lower()
        in_str = in_str.replace('\'', '')
        in_str = in_str.replace('`', '')
        tokens = filter(None, [STRIP_REGEX.sub(' ', LINKS_RE.sub('', each)).strip() for each in in_str.split(' ')])
        return tokens

    def sticky_score(self, segment):
        """
        Calculate the stickiness score of a segment.
        """
        scp = self.get_scp(segment)
        l_normal_factor = self.normalize_seg_length(len(segment))
        q_score = self.wiki_keyphraseness(segment)
        score = 2/(1 + np.exp(-1 * scp)) \
                * np.exp(q_score) \
                * l_normal_factor
        self.logger.debug("%s : SCP: %s, l_score: %s, q_score: %s, total %s" % (' '.join(segment), scp, l_normal_factor, q_score, score))
        return score

    def wiki_keyphraseness(self, segment):
        '''
        Q(s) Length Normalization
        '''
        q_score = self.wiki_q_hash.get(' '.join(segment), 0)
        return float(q_score)
   
    def normalize_seg_length(self, seg_length):
        '''
        L(s) Length Normalization
        '''
        factor = 1
        if seg_length > 1:
            factor = float(seg_length - 1)/seg_length
        return factor

    def get_scp(self, segment):
        '''
        Global P(s)
        '''
        n = len(segment)
        if n == 1:
            scp = 2 * self.cache.get(' '.join(segment))
        else:
            v = [self.cache[' '.join(segment[:i])] + self.cache[' '.join(segment[i:])] for i in range(1, n)]
            segment_str = ' '.join([each.strip() for each in segment])
            score = self.cache.get(segment_str)
            scp = 2*score - np.log((sum(np.exp(v))/(n - 1)))
        return scp

    def preprocess(self, toks):
        all_grams = list(set(self.find_all_grams(toks)))
        lm = LangModel('body')
        pvals = lm.get_jp(all_grams)
        for k in pvals.keys():
            pvals[k] = np.log(pow(10, pvals[k]))
        self.cache.update(pvals)

    def segment(self, in_str):
        """
        Segmentation algorithm as given in the paper
        L : no. words in the string
        """
        words = self.split_to_words(in_str)
        self.preprocess(words)
        S = defaultdict(list) # segments of segment starting at i
        L = len(words)
        self.logger.info(u"In str : %d segemnts, %s", L, in_str)
        for i in xrange(L):
            current_segment = words[:i+1]
            if i < self.U:
                current_score = self.sticky_score(current_segment)
                S[i].append(([current_segment], current_score))
                self.logger.debug(u"Current Segment: Start: %s, len: %s, Score: %0.5f, %s", \
                        i, len(current_segment), current_score, current_segment)
            # Do sub-segments
            for j in xrange(i):
                if i - j < self.U:
                    seg_1 = current_segment[:j+1]
                    seg_2 = current_segment[j+1:]
                    score_2 = self.sticky_score(seg_2)
                    self.logger.debug(u"Consider: (%s, %s), %s ", j, i, current_segment[j:])
                    self.logger.debug(u"Considered Segment: Start: %s, end: %s, Score: %0.5f, %s", j+1, i, score_2, current_segment[j+1:])
                    # update segment
                    new_segs = [(seg + [seg_2], seg_score + score_2) for (seg, seg_score) in S[j]]
                    S[i].extend(new_segs)
                # Pick top E subsegments only
                top_sub_segs = sorted(S[i], key=itemgetter(1), reverse=True)[:self.E]
                S[i] = top_sub_segs
            self.logger.debug(u"Got %s for %s", len(S[i]), i)
        self.logger.debug(pformat((S[L-1])))
        return S[L-1][0][0]



if __name__ == '__main__':
    sample = [
            u'youth olympic games sailing competition',
            u'vote sdp',
            u'"leo messi is better player than cristiano ronaldo"',
            u'''French leading daily Le Monde said in editorial, "the horizon of Indian democracy has been oddly clouded since the coming to power of Modi." ''',
            u'''1st sentence: "Antonin Scalia...devoted his professional life to making the [US] a less fair, less tolerant, and less admirable democracy"''',
            u'''Can @SAfridiOfficial lead Pakistan to another #WT20 title at ICC World Twenty20 India 2016? http://bit.ly/WT20SquadsAnnounced … ''',
    ]
    segmenter_obj = Segmenter()
    for each in sample:
        print each
        s = segmenter_obj.segment(each)
        print "Best Segmentation : "
        print '[', ' ]['.join([' '.join(x) for x in s]), ']'
        print
