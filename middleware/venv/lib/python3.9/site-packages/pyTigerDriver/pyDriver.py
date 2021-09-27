# -*- coding: utf-8 -*-


import re
import io
import base64
import json
import logging
import codecs
import datetime
import sys
from os import getenv
from os.path import expanduser, isfile

from .misc import quote_plus, urlencode, is_ssl, HTTPConnection, HTTPSConnection, ExceptionAuth

if is_ssl:
    import ssl


class ExceptionRecursiveRet(Exception):
    pass


class AuthenticationFailedException(Exception):
    pass


class ExceptionCodeRet(Exception):
    pass


PREFIX_CURSOR_UP = "__GSQL__MOVE__CURSOR___UP__"
PREFIX_CLEAN_LINE = "__GSQL__CLEAN__LINE__"
PREFIX_INTERACT = "__GSQL__INTERACT__"
PREFIX_RET = "__GSQL__RETURN__CODE__"
PREFIX_COOKIE = "__GSQL__COOKIES__"

FILE_PATTERN = re.compile("@[^@]*[^;,]")
PROGRESS_PATTERN = re.compile("\\[=*\\s*\\]\\s[0-9]+%.*")
COMPLETE_PATTERN = re.compile("\\[=*\\s*\\]\\s100%[^l]*")
TOKEN_PATTERN = re.compile("- Token: ([^ ]+) expire at: (.+)")

NULL_MODE = 0
VERTEX_MODE = 1
EDGE_MODE = 2
GRAPH_MODE = 3
JOB_MODE = 4
QUERY_MODE = 5
TUPLE_MODE = 6

CATALOG_MODES = {
    "Vertex Types": VERTEX_MODE,
    "Edge Types": EDGE_MODE,
    "Graphs": GRAPH_MODE,
    "Jobs": JOB_MODE,
    "Queries": QUERY_MODE,
    "User defined tuples": TUPLE_MODE
}


def _is_mode_line(line):
    return line.endswith(":")


def _get_current_mode(line):
    return CATALOG_MODES.get(line[:-1], NULL_MODE)


def _parse_catalog(lines):
    vertices = []
    edges = []
    graphs = []
    jobs = []
    queries = []
    tuples = []

    current_mode = NULL_MODE

    for line in lines:
        line = line.strip()
        if _is_mode_line(line):
            current_mode = _get_current_mode(line)
            continue

        if line.startswith("- "):
            line = line[2:]
            if current_mode == VERTEX_MODE:
                e = line.find("(")
                vertices.append(line[7:e])
            elif current_mode == EDGE_MODE:
                s = line.find("EDGE ") + 5
                e = line.find("(")
                edges.append(line[s:e])
            elif current_mode == GRAPH_MODE:
                s = line.find("Graph ") + 6
                e = line.find("(")
                graphs.append(line[s:e])
            elif current_mode == JOB_MODE:
                s = line.find("JOB ") + 4
                e = line.find(" FOR GRAPH")
                jobs.append(line[s:e])
            elif current_mode == QUERY_MODE:
                e = line.find("(")
                queries.append(line[:e])
            elif current_mode == TUPLE_MODE:
                e = line.find("(")
                tuples.append(line[:e].strip())
    return {
        "vertices": vertices,
        "edges": edges,
        "graphs": graphs,
        "jobs": jobs,
        "queries": queries,
        "tuples": tuples
    }


def _parse_secrets(lines):
    secrets = {}
    current = ""
    for line in lines:
        if line.startswith("- Secret: "):
            current = line[len("- Secret: "):]
            secrets[current] = {}
        elif line.startswith("- Alias: "):
            secrets[current]["alias"] = line[len("- Alias: "):]
        elif line.startswith("- GraphName: "):
            secrets[current]["graph"] = line[len("- GraphName: "):]
        elif line.startswith("- Token: "):
            m = TOKEN_PATTERN.match(line)
            if m:
                token, expire = m.groups()
                expire_datetime = datetime.datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
                if "tokens" not in secrets[current]:
                    secrets[current]["tokens"] = []
                secrets[current]["tokens"].append((token, expire_datetime))

    return secrets


def _secret_for_graph(secrets, graph):
    for k, v in secrets.items():
        if v["graph"] == graph:
            return k


def get_option(option, default=""):
    try:
        cfg_path = "tiger.cfg"  # expanduser
        with open(cfg_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(option):
                    values = line.split()
                    if len(values) >= 2:
                        return values[1]
    except:
        pass
    return default


VERSION_COMMIT = {
    "2.4.0": "f6b4892ad3be8e805d49ffd05ee2bc7e7be10dff",
    "2.4.1": "47229e675f792374d4525afe6ea10898decc2e44",
    "2.5.0": "bc49e20553e9e68212652f6c565cb96c068fab9e",
    "2.5.2": "291680f0b003eb89da1267c967728a2d4022a89e",
    "2.6.0": "6fe2f50ab9dc8457c4405094080186208bd2edc4",
    "2.6.2": "47be618a7fa40a8f5c2f6b8914a8eb47d06b7995",
    "3.0.0": "c90ec746a7e77ef5b108554be2133dfd1e1ab1b2",
    "3.0.5": "a9f902e5c552780589a15ba458adb48984359165",
    "3.1.0": "e9d3c5d98e7229118309f6d4bbc9446bad7c4c3d",
    "3.1.1": "375a182bc03b0c78b489e18a0d6af222916a48d2",
    "3.1.2": "3887cbd1d67b58ba6f88c50a069b679e20743984",
}


class GSQL_Client(object):

    def __init__(self, server_ip="127.0.0.1", username="tigergraph", password="tigergraph", cacert="",
                 version="", commit="", gsPort="14240", restpp="9000", debug=False):
        self.debug = debug
        self._logger = logging.getLogger("gsql_client.Client")
        self._server_ip = server_ip
        self._username = username
        self._password = password
        self.ExceptionDetected = False
        self.ExceptionCode = ""
        self.ExceptionText = ""
        if commit:
            self._client_commit = commit
        elif version in VERSION_COMMIT:
            self._client_commit = VERSION_COMMIT[version]
        else:
            self._client_commit = ""

        self._version = version

        if self._version and self._version >= "2.3.0":
            self._abort_name = "abortclientsession"
        else:
            self._abort_name = "abortloadingprogress"

        if cacert and is_ssl:
            self._context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            self._context.check_hostname = False
            self._context.verify_mode = ssl.CERT_REQUIRED
            self._context.load_verify_locations(cacert)
            self._protocol = "https"
        else:
            self._context = None
            self._protocol = "http"

        self.base64_credential = base64.b64encode(
            "{0}:{1}".format(self._username, self._password).encode("utf-8")).decode("utf-8")

        self._base_url = "/gsqlserver/gsql/"  #
        if ":" not in server_ip:
            self._server_ip = "{0}:{1}".format(server_ip, gsPort)


        self._initialize_url()

        self.graph = ""
        self.session = ""
        self.properties = ""

        self.authorization = 'Basic {0}'.format(self.base64_credential)

    def _initialize_url(self):
        self.command_url = self._base_url + "file" # Changed for multi line support ...
        self.version_url = self._base_url + "version"
        self.help_url = self._base_url + "help"
        self.login_url = self._base_url + "login"
        self.reset_url = self._base_url + "reset"
        self.file_url = self._base_url + "file"
        self.dialog_url = self._base_url + "dialog"

        self.info_url = self._base_url + "getinfo"
        self.abort_url = self._base_url + self._abort_name

    def _get_cookie(self):

        cookie = {}
        cookie["fromGsqlClient"] = True
        cookie["fromGraphStudio"] = True

        if self.graph:
            cookie["graph"] = self.graph

        if self.session:
            cookie["session"] = self.session

        if self.properties:
            cookie["properties"] = self.properties

        if self._client_commit:
            cookie["commitClient"] = self._client_commit

        return cookie

    def _set_cookie(self, cookie_str):

        cookie = json.loads(cookie_str)
        self.session = cookie.get("session", "")
        self.graph = cookie.get("graph", "")
        self.properties = cookie.get("properties", "")

    def _setup_connection(self, url, content, cookie={}, auth=True):

        if cookie == None:
            cookie = self._get_cookie()

        cookie["fromGsqlClient"] = True
        cookie["fromGraphStudio"] = True
        if self._protocol == "https":
            ssl._create_default_https_context = ssl._create_unverified_context
            conn = HTTPSConnection(self._server_ip)
        else:
            conn = HTTPConnection(self._server_ip)
        encoded = quote_plus(content.encode("utf-8"))
        headers = {
            "Content-Language": "en-US",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Java/1.8.0",
            "Cookie": json.dumps(self._get_cookie()) if cookie is None else json.dumps(cookie)
        }

        if auth:
            headers["Authorization"] = self.authorization
            conn.request("POST", url, encoded, headers)
        else:
            conn.request("POST", url, self.base64_credential, headers)
        return conn

    def _request(self, url, content, handler=None, cookie=None, auth=True):
        response = None
        if cookie == None:
            cookie = {}
            cookie = self._get_cookie()
        try:
            r = self._setup_connection(url, content, cookie, auth)
            response = r.getresponse()
            ret_code = response.status
            if ret_code == 401:
                raise AuthenticationFailedException("Invalid Username/Password!")
            if handler:
                reader = codecs.getreader("utf-8")(response)
                return handler(reader)
            else:
                return response.read().decode("utf-8")
        finally:
            if response:
                response.close()

    def _dialog(self, response):

        self._request(self.dialog_url, response)

    def _command_interactive(self, url, content, ans="", out=False):

        def __handle__interactive(reader):

            res = []

            for line in reader:

                line = line.strip()

                if line.startswith(PREFIX_RET):
                    _, ret = line.split(",", 1)
                    ret = int(ret)
                    if ret != 0:
                        self.ExceptionDetected = True
                        # raise ExceptionCodeRet(ret)
                elif line.startswith(PREFIX_INTERACT):
                    _, it, ik = line.split(",", 2)
                    if it in {"DecryptQb", "AlterPasswordQb", "CreateUserQb", "CreateTokenQb", "ClearStoreQb"} \
                            and ans:
                        self._dialog("{0},{1}".format(ik, ans))
                elif line.startswith(PREFIX_COOKIE):
                    _, cookie_s = line.split(",", 1)
                    self._set_cookie(cookie_s)
                elif line.startswith(PREFIX_CURSOR_UP):
                    values = line.split(",")
                    print("\033[" + values[1] + "A")
                elif line.startswith(PREFIX_CLEAN_LINE):
                    print("\033[2K")
                elif PROGRESS_PATTERN.match(line):
                    if COMPLETE_PATTERN.match(line):
                        line += "\n"
                    # else:
                    #     print("\r" + line)
                    #     sys.stdout.flush()
                else:
                    if out:
                        print(line)
                    res.append(line)
            return res

        return self._request(url, content, __handle__interactive)

    def login(self, commit_try="", version_try=""):

        if self._client_commit == "" and commit_try == "":
            # print('\033[33m' + "======= NO Version defined ============")

            for k in VERSION_COMMIT:
                # print( '\033[33m' + "==== Trying Version : {}".format(k))

                if (self.login(version_try=k, commit_try=VERSION_COMMIT[k]) == True):
                    # print('\x1b[6;30;42m' + "Succeded ! your version is {}".format(k) + '\x1b[0m')

                    break
                else:
                    CRED = '\033[91m'
                    CEND = '\033[0m'
                    # print(CRED + "Failed to connect version <> {}".format(k) + CEND)

                # import time
                # time.sleep(2)
        elif commit_try != "":
            self._client_commit = commit_try
            self._version = version_try
        response = None

        try:
            Cookies = {}
            Cookies['clientCommit'] = self._client_commit
            r = self._setup_connection(self.login_url, self.base64_credential, cookie=Cookies, auth=False)
            response = r.getresponse()
            ret_code = response.status
            # print(response.status)
            if ret_code == 200:
                content = response.read()
                res = json.loads(content.decode("utf-8"))
                # print(res)
                import time
                time.sleep(1)
                if "License expired" in res.get("message", ""):
                    raise Exception("TigerGraph Server License is expired! Please update your license!")

                compatible = res.get("isClientCompatible", True)
                if not compatible:
                    # print("This client is not compatible with target TigerGraph Server!  Please specify a correct version when creating this client!")
                    return False

                if res.get("error", False):
                    print(res)
                    if "Wrong password!" in res.get("message", ""):
                        raise ExceptionAuth("Invalid Username/Password!")
                    else:
                        raise Exception("Login failed!")
                else:
                    self.session = response.getheader("Set-Cookie")
                    return True
        finally:
            if response:
                response.close()

    def get_auto_keys(self):

        keys = self._request(self.info_url, "autokeys", cookie=self.session)
        return keys.split(",")

    def quit(self):

        self._request(self.abort_url, self._abort_name)

    def run_file(self, path):
        content = self._load_file_recursively(path)
        return self._command_interactive(self.file_url, content)

    def run_multiple(self, lines):
        return self._command_interactive(self.file_url, "\n".join(lines))

    def version(self):
        return self._command_interactive(self.version_url, "version")

    def help(self):
        return self._command_interactive(self.help_url, "help")

    def query(self, content,graph="", ans=""):
        self.graph = graph
        return self._command_interactive(self.command_url, content, ans)

    def use(self, graph):

        return self._command_interactive(self.command_url, "use graph {0}".format(graph))

    def catalog(self):

        lines = self._command_interactive(self.command_url, "ls", out=False)
        return _parse_catalog(lines)

    def get_secrets(self, graph_name):
        if self.graph != graph_name:
            self.use(graph_name)
        lines = self.query("show secret")
        return _parse_secrets(lines)

    def get_secret(self, graph_name, create_alias=None):
        secrets = self.get_secrets(graph_name)
        s = _secret_for_graph(secrets, graph_name)
        if s:
            return s
        elif create_alias:
            lines = self.query("create secret {0}".format(create_alias))
            return lines[0].split()[2]

    def _load_file_recursively(self, file_path):
        return self._read_file(file_path, set())

    def _read_file(self, file_path, loaded):
        if not file_path or not isfile(file_path):
            self._logger.warn("File \"" + file_path + "\" does not exist!")
            return ""

        if file_path in loaded:
            self._logger.error("There is an endless loop by using @" + file_path + " cmd recursively.")
            raise ExceptionRecursiveRet(file_path)
        else:
            loaded.add(file_path)

        res = ""
        with io.open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if FILE_PATTERN.match(line):
                    res += self._read_file(line[1:], loaded) + "\n"
                    continue
                res += line + "\n"
        return res



