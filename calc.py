#!/usr/bin/python
'''
A command-line calculator over streams of numbers.
Requires numpy for 'hist' and 'median'.

  For example:

# create a file with 100 random numbers, 1 per line
$ jot -r 100 > /tmp/random

# the max, min, mean of that random data
$ calc.py max /tmp/random
100.0
$ calc.py min /tmp/random
1.0
$ calc.py mean /tmp/random
48.86

# the median, using pipes instead of the file name
$ cat /tmp/random | calc.py median
51.0

# chaining commands -- exponentiating, then adding the numbers
$ cat /tmp/random | calc.py exp | calc.py sum
8.22200074586e+43

# print a histogram of random data (10 bins by default)
$ jot -r 100 | calc.py hist
[ 3.00,12.30): ############
[12.30,21.60): ########
[21.60,30.90): #######
[30.90,40.20): #########
[40.20,49.50): ###############
[49.50,58.80): #########
[58.80,68.10): #########
[68.10,77.40): #######
[77.40,86.70): ###############
[86.70,96.00]: #########

# print a histogram of random data with T number of bins
$ jot -r 100 | calc.py hist 21
[    1,  5.7): #######
[  5.7,   10): ##
[   10,   15): ##
[   15,   20): ######
[   20,   25): ######
[   25,   29): ##########
[   29,   34): ####
[   34,   39): #####
[   39,   43): ###
[   43,   48): #####
[   48,   53): ####
[   53,   58): #
[   58,   62): #####
[   62,   67): ####
[   67,   72): #######
[   72,   76): ##
[   76,   81): #####
[   81,   86): ####
[   86,   91): ######
[   91,   95): #####
[   95,1e+02]: #######

# same thing, but logarithmic histogram bins
$ jot -r 100 | calc.py log | calc.py hist
[0.00,0.46): ###
[0.46,0.92): ##
[0.92,1.38):
[1.38,1.84): ###
[1.84,2.30): ###
[2.30,2.76): #####
[2.76,3.22): ############
[3.22,3.68): ###########
[3.68,4.14): #############################
[4.14,4.60]: ################################

$ jot -r 100 | calc.py summary
size	min	  mean	  median	max	    var	    std_dev
100	    1.0	  53.21	  56.0	    99.0	809.17	28.45


'''
from __future__ import division
import math as m
from itertools import imap

def hist_formatter(x, tick_char = '#', max_width = 80):
  '''prints a histogram'''
  (vals, bins) = x
  s_bins = ['%0.2g' % b for b in bins]
  max_bin_len = max(len(x) for x in s_bins)
  s_bins = [x.rjust(max_bin_len) for x in s_bins]
  max_val = max(vals)
  if max_val + 5 + (max_bin_len*2) > max_width:
    max_available_width = max_width - 5 - (max_bin_len*2)
    vals = [ max_available_width * v // max_val for v in vals]

  s = '\n'.join('[%s,%s): %s' % (s_bins[i], s_bins[i+1], tick_char*vals[i]) \
                for i in xrange(len(vals)-1))
  s = s + '\n[%s,%s]: %s' % (s_bins[len(vals)-1], s_bins[len(vals)],
                                tick_char*vals[-1])
  return s

def s_mean_var(data):
  '''calculates the mean & variance with minimal intermediate data structures.
  see http://www.johndcook.com/standard_deviation.html'''
  m_n = 0
  m_oldM, m_newM, m_oldS, m_newS = 0.0, 0.0, 0.0, 0.0
  for x in data:
    m_n += 1
    if m_n == 1:
      m_oldM = m_newM = x
      m_oldS = 0.0
    else:
      m_newM = m_oldM + (x - m_oldM) / m_n
      m_newS = m_oldS + (x - m_oldM)*(x - m_newM)
      m_oldM, m_oldS = m_newM, m_newS
  mean = m_newM if m_n > 0 else 0.0
  var = m_newS / (m_n - 1) if m_n > 1 else 0.0
  yield (mean, var)

def s_mean(data): yield s_mean_var(data).next()[0]
def s_var(data): yield s_mean_var(data).next()[1]
def s_std(data): yield m.sqrt(s_var(data).next())

def s_cumsum(data):
  s = 0
  for x in data:
    s += x
    yield s

def s_cumprod(data):
  prod = 1.0
  for x in data:
    prod *= x
    yield prod

def s_prod(data):
  prod = 1.0
  for x in data: prod *= x
  yield prod

s_exp = lambda data: imap(m.exp, data)
s_log = lambda data: imap(m.log, data)
s_sqrt = lambda data: imap(m.sqrt, data)
def s_sum(data): yield sum(data)
def s_max(data): yield max(data)
def s_min(data): yield min(data)

num_hist_bins = 10
def hist(data):
  try:
    import numpy as n
  except ImportError:
    raise ValueError('numpy needed to run \'hist\'')
  yield n.histogram(list(data),bins=num_hist_bins)

def median(data):
  try:
    import numpy as n
  except ImportError:
    raise ValueError('numpy needed to run \'median\'')
  yield n.median(list(data))

def summary(data):
  try:
    import numpy as np
  except ImportError:
    raise ValueError('numpy needed to run \'summary\'')
  data2 = list(data)  #store all data
  print("size\tmin\tmean\tmedian\tmax\tvar\tstd_dev")
  return ["\t".join([str(len(data2)),str(round(min(data2),2)),str(round(np.mean(data2),2)), str(round(np.median(data2),2)), str(round(max(data2),2)), str(round(np.var(data2),2)), str(round(np.std(data2),2))])]

class Command(object):
  '''An individual command, deals with execution & formatting'''

  def __init__(self, function = None, formatter = str, help = None):
    self.formatter = formatter
    self.function = function
    self.help = help

  def __call__(self, data):
    return self.function(data) if self.function else data

  def process(self, data):
    return imap(self.formatter, self(data))

class CommandProcessor(object):
  '''Handles processing commands'''
  def __init__(self):
    self._commands = {}

  def register_command(self, name, command = None, function = None,
                       formatter = str, help = None):
    if command:
      self._commands[name] = command
    else:
      self._commands[name] = Command(function, formatter, help)

  def valid_command(self, command):
    return command in self._commands

  def command_list(self):
    all_commands_help = ['\t%s\t%s' % (name, c.help) for (name, c) in \
                      sorted(self._commands.items())]
    return '\n'.join(all_commands_help)

  def process(self, command, data):
    try:
      c = self._commands[command]
    except KeyError, e:
      raise ValueError('Command not found: %s' % command)
    return c.process(data)

c = CommandProcessor()
c.register_command('sum', function=s_sum, help='Add a list of numbers')
c.register_command('add', function=s_sum, help='see sum')
c.register_command('sqrt', function=s_sqrt, help='Square Root')
c.register_command('max', function=s_max, help='Max')
c.register_command('min', function=s_min, help='Min')
c.register_command('prod', function=s_prod,
                   help='Multiply a list of numbers')
c.register_command('hist', function=hist,
                   formatter=hist_formatter, help='Produce a histogram')
c.register_command('mean', function=s_mean, help='Mean')
c.register_command('median', function=median, help='Median')
c.register_command('var', function=s_var, help='Variance')
c.register_command('std', function=s_std, help='Standard Deviation')
c.register_command('cumsum', function=s_cumsum,  help='Cumulative sum')
c.register_command('cumprod', function=s_cumprod, help='Cumulative product')
c.register_command('exp', function=s_exp,
                   help='Exponentiate every element in the list')
c.register_command('log', function=s_log,
                   help='Take the log of every element in the list')
c.register_command('print', function=None,
                   help='Just print the (cleaned) input')
c.register_command('help', function=None, help="Print this message")
c.register_command('mean_var', function=s_mean_var,
                   help='Computes mean & variance with one pass')
c.register_command('summary', function=summary, help='Summary statistics (not streaming mode)')


if __name__ == "__main__":
  import sys, gzip, bz2
  def help_quit(i, e = None):
    help = '''Usage: calc.py [command] [files or -]
Reads a list of numbers from the files or standard input if files are missing
and performs the calculation specified by the command.
Available Commands:
%s''' % c.command_list()
    print >> sys.stderr, help
    if e: print >> sys.stderr, e
    sys.exit(i)

  def _read_stdin():
    while True:
      try:
        yield raw_input()
      except EOFError:
        break

  def _read_file(*filenames):
    extensions = {
      'gz': gzip.open,
      'bz2': lambda x: bz2.BZ2File(x, mode='rU'),
      }
    for f in filenames:
      ext = f.rsplit('.', 1)[-1]
      fin = extensions.get(ext, open)(f)
      for line in fin: yield line

  def read(*input):
    if len(input) > 0:
      return _read_file(*input)
    else:
      return _read_stdin()

  if len(sys.argv) < 2: help_quit(1)

  command = sys.argv[1]

  if command == 'help': help_quit(0)

  start_idx = 2
  if command == 'hist' and len(sys.argv)>2 and all([i.isdigit() for i in sys.argv[2]]) :
    num_hist_bins = float(sys.argv[2])
    start_idx = 3

  l = (float(x.strip()) for x in read(*sys.argv[start_idx:]) \
          if len(x.strip()) > 0 and x[0] != '#')

  try:
    for x in c.process(command, l): print x
  except ValueError, e:
    help_quit(1, e)
