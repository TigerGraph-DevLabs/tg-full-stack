# -*- coding: utf-8 -*-

from .misc import ExceptionAuth
from .pyDriver import GSQL_Client, ExceptionRecursiveRet, ExceptionCodeRet

class Client():
    def __init__(self, server_ip="127.0.0.1", username="tigergraph", password="tigergraph", cacert=""
                 ,version="", commit="",gsPort="14240",restpp="9000",debug=False):

        self.Gsql = GSQL_Client(server_ip=server_ip, username=username, password=password, cacert=cacert
                           ,version=version, commit=commit,gsPort=gsPort,restpp=restpp,debug=debug)