"""test for rds2hdf5"""

import math

from rds2hdf5 import rds2hdf, readfromhdf

# 0 0   0.3 0   0.4
# 0 0   0.5 0.7 0
# 0 0   0   0   0
# 0 0.2 0.6 0   0
# 0 0.2 1.4 0.7 0.4  (column sum)

# umifrac values: (value * 1000 / column sum)
# 0 0        3000/1.4 0        4000/0.4
# 0 0        5000/1.4 7000/0.7 0
# 0 0        0        0        0
# 0 2000/0.2 6000/1.4 0        0

# 0 0        2142.857 0        10000
# 0 0        3571.428 10000    0
# 0 0        0        0        0
# 0 10000    4285.714 0        0

# HDF5 file must contain: [ (column, expressionValue)] (0-indexing)
#   g1: [(3,2142.8), (5, 10000)]
#   g2: [(3,3571.428), (4, 10000)]
#   g3: []
#   g4: [(2,10000), (3, 4285.714 )]

# The following File must be created with R script createExample.R
INPUT_FILE = "example.RDS"
OUTPUT_FILE = "example.hdf5"
rds2hdf(INPUT_FILE, OUTPUT_FILE)

g1 = readfromhdf(OUTPUT_FILE, "g1")
g2 = readfromhdf(OUTPUT_FILE, "g2")
g3 = readfromhdf(OUTPUT_FILE, "g3")
g4 = readfromhdf(OUTPUT_FILE, "g4")

assert len(g1) == 2 and len(g2) == 2 and len(g3) == 0 and len(g4) == 2

assert math.isclose(g1["c3"], 2142.85, rel_tol=0.001)
assert math.isclose(g1["c5"], 10000, rel_tol=0.001)
assert math.isclose(g2["c3"], 3571.428, rel_tol=0.001)
assert math.isclose(g2["c4"], 10000, rel_tol=0.001)
assert math.isclose(g4["c2"], 10000, rel_tol=0.001)
assert math.isclose(g4["c3"], 4285.71, rel_tol=0.001)
