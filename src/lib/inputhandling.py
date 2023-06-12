import os

import lib.graph as graph

Lines = [line.strip().split(',') for line in
         open('./lib/edges.csv', 'r').readlines() if not line.strip()
         in os.getenv("BLACKLIST", "").split(";")]
G = graph.constructGraph(Lines)
