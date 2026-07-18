import networkx as nx

class KnowledgeGraph:
    def __init__(self, store):
        self._graph = nx.Graph()
    async def init(self):
        pass
    async def export_cytoscape(self):
        return {"elements": []}
