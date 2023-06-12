import networkx as nx


def constructGraph(lines):
    G = nx.DiGraph()
    nodes = [str(item) for sublist in list([int(x[0]), int(x[1])]
                                           for x in lines) for item in sublist]
    G.add_nodes_from(nodes)
    G.add_edges_from([(line[0], line[1]) for line in lines])
    return G


def Recurse(graph, node, succ, graphfunction, recursor):
    if not node in graph:
        return succ
    for g in graphfunction(node):
        if not g in succ:
            succ.append(g)
            recursor(graph, g, succ)
    return succ


def getDecendants(graph, node, succ):
    return Recurse(graph, node, succ, graph.successors, getDecendants)


def getAncestors(graph, node, succ):
    return Recurse(graph, node, succ, graph.predecessors, getAncestors)


def getRelated(graph, node, succ):
    return Recurse(graph, node, succ, lambda n: list(graph.predecessors(n)) + list(graph.successors(n)), getRelated)
