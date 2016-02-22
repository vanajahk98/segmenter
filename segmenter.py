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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)

# System params
U = 5 # Max length of a segment
E = 5 # Max sub segments of a segment to be considered
REGEX = re.compile('[%s]' % re.escape(punctuation))



def find_ngrams(in_toks, n):
      return zip(*[in_toks[i:] for i in range(n)])

def find_all_grams(in_toks):
    all_grams = []
    for i in xrange(1, U+1):
        all_grams.extend([' '.join(each) for each in find_ngrams(in_toks, i)])
    return all_grams

def split_to_words(in_str):
    in_str = in_str.lower()
    in_str = in_str.replace('.', ' ')
    in_str = REGEX.sub('', in_str)
    tokens = filter(None, [each.strip() for each in in_str.split(' ')])
    return tokens

def sticky_score(segment, cache={}):
    """
    Calculate the stickiness score of a segment.
    """
    segment_str = ' '.join([each.strip() for each in segment])
    score = cache.get(segment_str)
    if not score:
        lm = LangModel('body')
        score = lm.get_jp([segment_str])[segment_str]
    return score

def preprocess(toks):
    all_grams = list(set(find_all_grams(toks)))
    lm = LangModel('body')
    pvals = lm.get_jp(all_grams)
    pprint(pvals)
    return pvals

def segment(in_str):
    """
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
            continue # ?????
        # Do sub-segments
        for j in xrange(i):
            if i - j <= U:
                seg_1 = current_segment[:j+1]
                seg_2 = current_segment[j+1:]
                score_2 = sticky_score(seg_2, cache)
                logger.debug(u"Split: (%s, %s, %s), %s ", 0, j, i, current_segment)
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
    T = u'''Be really careful with those early entrance polls. Not intended for making projections. Weren't accurate in Iowa. '''
    T = u'this youth olympic games sailing competition'
    T = u'We have some delightful new food in the cafeteria. Awesome!!!'
    k = segment(T)
    print T
    print "Best Segmentation : "
    print '[', ' ]['.join([' '.join(each) for each in k]), ']'
