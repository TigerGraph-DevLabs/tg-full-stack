from typing import Optional
from fastapi import FastAPI
import config as Credential
from fastapi.middleware.cors import CORSMiddleware
import pyTigerGraph as tg

conn = tg.TigerGraphConnection(host=Credential.HOST, username=Credential.USERNAME, password=Credential.PASSWORD, graphname=Credential.GRAPHNAME)
conn.apiToken = conn.getToken(conn.createSecret())
app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/listPatients_Infected_By")
def readListPatients_Infected_By():
    gQuery = conn.runInstalledQuery("listPatients_Infected_By", {"p":2000000205})[0]['Infected_Patients']
    count = 0
    children = []
    for p in gQuery:
        children.append({
        "children": [],
        "collapsed": True,
        "id": str(count),
        "name": p[-3:] + "Patient",
        
        })
        count+=1
    
    result = {
        "name": "205 ROOT",
        "id": "root",
        "children": children,
        "style": {
            "fill": "#FFDBD9",
            "stroke":  "#FF6D67"
        }
    }
    return result



# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Optional[str] = None):
#     return {"item_id": item_id, "q": q}

# @app.get("/edgeCrawl")
# def getEdgeCrawl():
#     result = {"nodes":[], "edges":[]}
#     response = conn.runInstalledQuery("edgeCrawl")[0]['@@edgeList']
#     nodes = []
#     for object in response:
#         if( node.object["from_id"]):
#     return result

# @app.get("/allConnection")
# def getAllConnection():
#     data = {}
#     node = []
#     edges = []
#     objectN = {
#         "id":""
#     }
#     return conn.runInstalledQuery("allConnection", {"p":4100000006})

# @app.get("/allPersonId")
# def getAllPersonId():
#     return conn.getVertices("Patient")