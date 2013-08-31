#!/usr/bin/env python
'''github-pr-stats

Usage:
   github-pr-stats <user> <repo>
   github-pr-stats (-h | --help)

Options:
   -h --help           Show this screen.
'''

# May you recognize your weaknesses and share your strengths.
# May you share freely, never taking more than you give.
# May you find love and love everyone you find.

from __future__ import division

import signal
import sys
from collections import defaultdict, OrderedDict

from ascii_graph import Pyasciigraph
from docopt import docopt
from envoy import run
from github3 import authorize, login, GitHub
from numpy import array, median as calcMedian

# Stack traces are ugly; why would we want to print one on ctrl-c?
def nice_sigint(signal, frame):
   print("")
   sys.exit(0)
signal.signal(signal.SIGINT, nice_sigint)

arguments = docopt(__doc__)

# Use a stored OAuth token so we don't have to ask for the user's password
# every time (or save the password on disk!).
token = run('git config --global github-pr-stats.token').std_out.strip()
if not token:
   from getpass import getpass
   user = password = ''

   while not user:
      user = raw_input('Username: ')
   while not password:
      password = getpass('Password: ')

   auth = authorize(user, password,
                    scopes=['repo'],
                    note='github-pr-stats',
                    note_url='https://github.com/xiongchiamiov/github-pr-stats')
   token = auth.token
   # We need to un-unicode token for now.
   # https://github.com/kennethreitz/envoy/issues/34
   run("git config --global github-pr-stats.token '%s'" % str(token))
gh = login(token=token)

repo = gh.repository(arguments['<user>'], arguments['<repo>'])
stats = {
   'count': 0,
   'merged': 0,
   'daysOpen': [],
   'daysOpenHistogram': defaultdict(int),
   'comments': [],
   'commentsHistogram': defaultdict(int),
   'dayOfWeekCreated': OrderedDict(),
   'dayOfWeekClosed': OrderedDict(),
}
dayMapping = {
   0: 'M',
   1: 'T',
   2: 'W',
   3: 'R',
   4: 'F',
   5: 'Sa',
   6: 'Su',
}
for day in dayMapping.values():
   stats['dayOfWeekCreated'][day] = 0
   stats['dayOfWeekClosed'][day] = 0

progressMeter = 'Data fetches remaining:   0'
print progressMeter,
for pr in repo.iter_pulls(state='closed'):
   # We'll just assume we won't go over three digits of issues, which is
   # perhaps a bad assumption.
   print '\b\b\b\b%3d' % pr.number,
   sys.stdout.flush()
   
   daysOpen = (pr.closed_at - pr.created_at).days
   comments = len(list(pr.iter_comments()))
   stats['count'] += 1
   if pr.is_merged():
      stats['merged'] += 1
   stats['daysOpen'].append(daysOpen)
   stats['daysOpenHistogram'][daysOpen] += 1
   stats['comments'].append(comments)
   stats['commentsHistogram'][comments] += 1
   dayAbbreviation = dayMapping[pr.created_at.weekday()]
   stats['dayOfWeekCreated'][dayAbbreviation] += 1
   dayAbbreviation = dayMapping[pr.closed_at.weekday()]
   stats['dayOfWeekClosed'][dayAbbreviation] += 1
print '\b' * (len(progressMeter) + 1), # +1 for the newline

percentageMerged = round(100 - (stats['count'] / stats['merged']), 2)
print '%s%% (%s of %s) closed pulls merged.' % (percentageMerged, stats['merged'], stats['count'])

def print_report(subject):
   '''Do various calculations on the subject, then print the results.
   
   This should be like, 8 different functions or something, but bad API design
   is easier.
   '''
   # It'd be a lot nicer to do these calculations using
   # http://www.python.org/dev/peps/pep-0450/ or even
   # https://pypi.python.org/pypi/stats/ instead of the
   # sometimes-difficult-to-install Numpy.  But alas, we're stuck with that for
   # Python 2.x.
   data = array(stats[subject])
   mean = data.mean()
   median = calcMedian(data) # I don't know why narray doesn't have this as a method.
   stdDev = data.std()
   min = data.min()
   max = data.max()
   print '%s: %s (mean) %s (median) %s (std. dev.) %s (min) %s (max)' \
       % (subject, mean, median, stdDev, min, max)

   # Touch every value in the range to ensure the defaultdict counts them as
   # keys.  This allows us to make a histogram without gaps.
   for i in range(min, max):
      stats[subject+'Histogram'][i]
   
   print_histogram(subject+'Histogram')

def print_histogram(key, label=''):
   # Work around a bug in ascii_graph.
   # https://github.com/kakwa/py-ascii-graph/issues/3
   histogram = [(str(key), value) \
                for (key, value) \
                in stats[key].items()]
   graph = Pyasciigraph()
   for line in graph.graph(label, histogram):
      print line

print_report('daysOpen')
print_report('comments')
print_histogram('dayOfWeekCreated', 'Day of Week Created')
print_histogram('dayOfWeekClosed', 'Day of Week Closed')

