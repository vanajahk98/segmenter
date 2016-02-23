#!/usr/binenv python
#coding: utf-8

from collections import defaultdict
from operator import itemgetter
import logging
import sys
from random import random
from LangModel import LangModel
from string import punctuation
from pprint import pprint
import re
import numpy

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)

# System params
U = 5 # Max length of a segment
E = 5 # Max sub segments of a segment to be considered
REGEX = re.compile('[%s]' % re.escape(punctuation))

WIKI_Q_FILE_PATH = 'WikiQsEng/WikiQsEng.txt'

def load_wiki_q():
    d = {}
    with open(WIKI_Q_FILE_PATH) as f:
        for line in f:
            kwd, p = line.strip().rsplit(',', 1)
            kwd = kwd.replace('_', ' ')
            kwd = REGEX.sub(' ', kwd)
            d[kwd] = max(float(p), float(0))
    return d

WIKI_Q = load_wiki_q()

def find_ngrams(in_toks, n):
      return zip(*[in_toks[i:] for i in range(n)])

def find_all_grams(in_toks):
    all_grams = []
    for i in xrange(1, U+1):
        all_grams.extend([' '.join(each) for each in find_ngrams(in_toks, i)])
    return all_grams

def split_to_words(in_str):
    in_str = in_str.lower()
    in_str = in_str.replace('\'', '')
    in_str = in_str.replace('`', '')
    in_str = REGEX.sub(' ', in_str)
    tokens = filter(None, [each.strip() for each in in_str.split(' ')])
    return tokens

def sticky_score(segment, cache={}):
    """
    Calculate the stickiness score of a segment.
    """
    scp = get_scp(segment, cache)
    l_normal_factor = normalize_seg_length(len(segment))
    q_score = wiki_keyphraseness(segment)
    score = 2/(1 + numpy.exp(-1 * scp)) \
            * numpy.exp(10*q_score) \
            * l_normal_factor
    print ' '.join(segment), "SCP: %s, l_score: %s, q_score: %s, total %s" % (scp, l_normal_factor, q_score, score)
    return score

def wiki_keyphraseness(segment):
    '''
    Q(s) Length Normalization
    '''
    q_score = WIKI_Q.get(' '.join(segment), 0)
    return float(q_score)
   
def normalize_seg_length(seg_length):
    '''
    L(s) Length Normalization
    '''
    factor = 1
    if seg_length > 1:
        factor = float(seg_length - 1)/seg_length
    return factor

def get_scp(segment, cache):
    '''
    Global P(s)
    '''
    n = len(segment)
    if n == 1:
        scp = 2*cache.get(' '.join(segment))
    else:
        v = [cache[' '.join(segment[:i])] + cache[' '.join(segment[i:])] for i in range(1, n)]
        segment_str = ' '.join([each.strip() for each in segment])
        score = cache.get(segment_str)
        scp = 2*score - (sum(numpy.exp(v))/(n - 1))
    return scp

def preprocess(toks):
    all_grams = list(set(find_all_grams(toks)))
    lm = LangModel('body')
    pvals = lm.get_jp(all_grams)
    return pvals

def segment(in_str):
    """
    Segmentation algorithm as given in the paper
    L : no. words in the string
    """
    words = split_to_words(in_str)
    cache = preprocess(words)
    S = defaultdict(list) # segments of segment starting at i
    L = len(words)
    logger.info(u"In str : %d segemnts, %s", L, in_str)
    for i in xrange(L):
        current_segment = words[:i+1]
        if i < U:
            current_score = sticky_score(current_segment, cache)
            S[i].append(([current_segment], current_score))
            logger.debug(u"Current Segment: Start: %s, len: %s, Score: %0.5f, %s", \
                    i, len(current_segment), current_score, current_segment)
            #continue # ?????
        # Do sub-segments
        for j in xrange(i):
            if i - j < U:
                seg_1 = current_segment[:j+1]
                seg_2 = current_segment[j+1:]
                score_2 = sticky_score(seg_2, cache)
                logger.debug(u"Consider: (%s, %s), %s ", j, i, current_segment[j:])
                logger.debug(u"Considered Segment: Start: %s, end: %s, Score: %0.5f, %s", j+1, i, score_2, current_segment[j+1:])
                # update segment
                new_segs = [(seg + [seg_2], seg_score + score_2) for (seg, seg_score) in S[j]]
                S[i].extend(new_segs)
            # Pick top E subsegments only
            top_sub_segs = sorted(S[i], key=itemgetter(1), reverse=True)[:E]
            S[i] = top_sub_segs
        logger.debug(u"Got %s for %s", len(S[i]), i)
    pprint(S[L-1])
    return S[L-1][0][0]



if __name__ == '__main__':
    T = u'''1st sentence: "Antonin Scalia...devoted his professional life to making the [US] a less fair, less tolerant, and less admirable democracy"'''
    T = u'youth olympic games sailing competition'
    T = u'''French leading daily Le Monde said in editorial, "the horizon of Indian democracy has been oddly clouded since the coming to power of Modi." '''
    '''
    k = segment(T)
    print T
    print "Best Segmentation : "
    print '[', ' ]['.join([' '.join(each) for each in k]), ']'
    '''
    cache = preprocess(split_to_words(T))
    for each in find_all_grams(split_to_words(T)):
        each = each.split()
        print  each, numpy.exp(get_scp(each, cache)), numpy.exp(cache[' '.join(each)])
