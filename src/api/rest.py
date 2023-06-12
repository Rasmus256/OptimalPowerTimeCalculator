from fastapi import FastAPI
from cachetools import TTLCache
import asyncio

import lib.graph as graph
from lib.inputhandling import G

resultcache = TTLCache(maxsize=30, ttl=60)
app = FastAPI()

def get_nodes_generic(startnode, element_name, graphfunction):
    if not (startnode, element_name) in resultcache:
        print(f"calculating value for {startnode}, {element_name}")
        resultcache[startnode, element_name] = graphfunction(G, startnode, [])
    else:
        print(f"got {startnode}, {element_name} from cache")
    return {element_name: resultcache[startnode, element_name]}

def add_startnode(startnode, dict):
    return {'startnode': startnode} | dict

@app.get("/api/reachable")
async def get_reachable_nodes(startnode: str):
    d = get_desc_nodes(startnode) 
    a = get_ancs_nodes(startnode) 
    r = get_rela_nodes(startnode)
    (d,a,r) = await asyncio.gather(d,a,r)
    return add_startnode(startnode, d | a | r)


@app.get("/api/descendants")
async def get_desc_nodes(startnode: str):
    return add_startnode(startnode, get_nodes_generic(startnode, 'descendants', graph.getDecendants))


@app.get("/api/ancestors")
async def get_ancs_nodes(startnode: str):
    return add_startnode(startnode,  get_nodes_generic(startnode, 'ancestors', graph.getAncestors))


@app.get("/api/related")
async def get_rela_nodes(startnode: str):
    return add_startnode(startnode,  get_nodes_generic(startnode, 'related', graph.getRelated))


@app.get("/healthz", status_code=204)
def healthcheck():
    return None
