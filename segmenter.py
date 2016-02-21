#!/usr/binenv python
#coding: utf-8

from collections import defaultdict
from operator import itemgetter
import logging
import sys
from random import random
from LangModel import LangModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)

# System params
U = 6 # Max length of a segment
E = 5 # Max sub segments of a segment to be considered

def sticky_score(segment):
    """
    Calculate the stickiness score of a segment.
    """
    segment_str = ' '.join([each.strip() for each in segment])
    lm = LangModel('body')
    score = lm.get_jp([segment_str])[0]
    return score
    #return random()
    #raise NotImplementedError

# split the string into words based in whitespaces
def split_to_words(in_str):
    return in_str.split()

def segment(in_str):
    """
    L : no. words in the string
    """
    words = split_to_words(in_str)
    S = defaultdict(list) # segments of segment starting at i
    L = len(words)
    logger.info(u"In str : %d segemnts, %s", L, in_str)
    for i in xrange(L):
        current_segment = words[:i+1]
        if i < U:
            current_score = sticky_score(current_segment)
            S[i].append(([current_segment], current_score))
            logger.info(u"Current Segment: Start: %s, len: %s, Score: %0.5f, %s", \
                    i, len(current_segment), current_score, current_segment)
            continue # ?????
        # Do sub-segments
        for j in xrange(i):
            if i - j <= U:
                seg_1 = current_segment[:j+1]
                seg_2 = current_segment[j+1:]
                score_2 = sticky_score(seg_2)
                logger.info(u"Split: (%s, %s, %s), %s ", 0, j, i, current_segment)
                logger.info(u"Considered Segment: Start: %s, end: %s, Score: %0.5f, %s", j+1, i, score_2, current_segment[j+1:])
                # update segment
                new_segs = [(seg + [seg_2], seg_score + score_2) for (seg, seg_score) in S[j]]
                S[i].extend(new_segs)
            # Pick top E subsegments only
            top_sub_segs = sorted(S[i], key=itemgetter(1), reverse=True)[:E]
            S[i] = top_sub_segs
        logger.info(u"Got %s for %s", len(S[i]), i)
    return S[L-1][0][0]



if __name__ == '__main__':
    T = u'''Be really careful with those early entrance polls. Not intended for making projections. Weren't accurate in Iowa. '''
    k = segment(T)
    print T
    print "Best Segmentation : "
    print '[', ' ]['.join([' '.join(each) for each in k]), ']'
