# import strawberry
import typing
import pyTigerGraph as tg
import config as Credential
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from strawberry.asgi import GraphQL

# def get_users():
#     gQuery = conn.runInstalledQuery("listPatients_Infected_By", {"p":2000000205})[0]['Infected_Patients']
#     result = gQuery[0]
#     return [User(result)]

# @strawberry.type
# class User:
#     id: str

# @strawberry.type
# class Query:
#     users: typing.List[User]= strawberry.field(resolver=get_users)

# @strawberry.type
# class Query:
#     @strawberry.field
#     def user(self) -> User:
#         return User(id="Nick")




# To create the schema
# schema = strawberry.Schema(query=Query)

# graphql_app = GraphQL(schema)


app = FastAPI()


try:
     conn = tg.TigerGraphConnection(host=Credential.HOST, username=Credential.USERNAME, password=Credential.PASSWORD, graphname=Credential.GRAPHNAME)
     conn.apiToken = conn.getToken(conn.createSecret())
     app = FastAPI()
except Exception as e:
    import time
    print(e)
    time.sleep(50000)

    

origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://192.168.4.53:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_route("/graphql", graphql_app)
# app.add_websocket_route("/graphql", graphql_app)

@app.get("/")
def read_root():
    return {"Hello":"World"}

@app.get("/listPatients_Infected_By")
def readListPatients_Infected_By():
     try:
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
     except:
          return []    


# {
#     "name":
#     "id":
#     "children":[{name, id, children}, {{name, id, children}, ...}]
# }