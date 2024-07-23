# This work is based on these projects:
# https://github.com/guillon/socks-relay
# https://github.com/rushter/socks5


import json
import selectors
import socket
import struct
from socketserver import ThreadingMixIn, TCPServer, BaseRequestHandler
import logging
import subprocess
import threading
import time
import socks
import requests


SOCKS_VERSION = 5
SOCKS5_ATYPE_IPV4 = 0x01
SOCKS5_ATYPE_DOMAIN = 0x03
SOCKS5_ATYPE_IPV6 = 0x04


class ConnectionInterrupted(Exception):
    pass


class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    pass


class SocksProxy(BaseRequestHandler):

    def setup(self):
        super(SocksProxy, self).setup()
        self.request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.resolve_map = {}

    def recv(self, sock, n):
        try:
            return sock.recv(n)
        except Exception as e:
            raise ConnectionInterrupted("in recv() %s: %s" % (sock, e))

    def recvall(self, sock, n):
        parts = []
        total = 0
        while total < n:
            try:
                part = sock.recv(n - total)
            except Exception as e:
                raise ConnectionInterrupted("in recvall() %s: %s" % (sock, e))
            if len(part) == 0:
                break
            total += len(part)
            parts.append(part)
        if total < n:
            raise ConnectionInterrupted(
                "in recvall() %s: unexpected end of stream" % sock
            )
        return b"".join(parts)

    def sendall(self, sock, msg):
        try:
            return sock.sendall(msg)
        except Exception as e:
            raise ConnectionInterrupted("sock.sendall %s: %s" % (sock, e))

    def generate_failed_reply(self, error_number):
        return struct.pack(
            "!BBBBIH", SOCKS_VERSION, error_number, 0, SOCKS5_ATYPE_IPV4, 0, 0
        )

    def resolve_addr_port(self, address, port):
        resolved = self.resolve_map.get("%s:%s" % (address, port))
        if resolved != None:
            resolved_address, resolved_port = resolved.rsplit(":", 1)
        else:
            resolved = self.resolve_map.get(address)
            if resolved != None:
                resolved_address, resolved_port = resolved, port
            else:
                resolved_address, resolved_port = address, port
        if (resolved_address, resolved_port) != (address, port):
            return self.resolve_addr_port(resolved_address, resolved_port)
        return (resolved_address, resolved_port)

    def exchange_loop(self, client, remote):
        sel = selectors.DefaultSelector()
        client.setblocking(False)
        sel.register(client, selectors.EVENT_READ, remote)
        remote.setblocking(False)
        sel.register(remote, selectors.EVENT_READ, client)

        counter = 0
        while len(sel.get_map().keys()) == 2:
            events = sel.select(secondaryTimeout if counter == 1 else primaryTimeout)
            counter += 1

            if not events:
                return False
            for key, mask in events:
                data = self.recv(key.fileobj, 4096)
                if len(data) > 0:
                    self.sendall(key.data, data)
                else:
                    sel.unregister(key.fileobj)

        sel.close()
        return True

    def print(self, msg):
        logger.debug(
            f'From "{self.client_address[0]}:{self.client_address[1]}" to "{self.server.proxy.host}:{self.server.proxy.port}": {msg}'
        )

    def handle(self):
        self.print("Accepting connection")

        try:
            # greeting header
            header = self.recvall(self.request, 2)
            version, nmethods = struct.unpack("!BB", header)

            # asserts socks 5
            assert version == SOCKS_VERSION
            assert nmethods > 0

            # get available methods
            methods = set(self.recvall(self.request, nmethods))
            if 0x00 not in methods:
                self.print("Authentication methods not available")
                self.sendall(
                    self.request,
                    struct.pack("!BB", SOCKS_VERSION, "NO ACCEPTABLE METHODS"),
                )
                return

            # send welcome message
            self.sendall(self.request, struct.pack("!BB", SOCKS_VERSION, 0x00))

            # request
            version, cmd, _, address_type = struct.unpack(
                "!BBBB", self.recvall(self.request, 4)
            )
            assert version == SOCKS_VERSION

            if address_type not in [SOCKS5_ATYPE_IPV4, SOCKS5_ATYPE_DOMAIN]:
                self.print(f"Address Type not supported: {address_type}")
                reply = self.generate_failed_reply(0x08)  # Address type not supported
                self.sendall(self.request, reply)
                return

            if address_type == SOCKS5_ATYPE_IPV4:
                address = socket.inet_ntoa(self.recvall(self.request, 4))
            elif address_type == SOCKS5_ATYPE_DOMAIN:
                domain_length = self.recvall(self.request, 1)[0]
                address = self.recvall(self.request, domain_length).decode("ascii")
            port = struct.unpack("!H", self.recvall(self.request, 2))[0]

            if cmd != 0x01:
                self.print(f"Command not supported: {cmd}")
                reply = self.generate_failed_reply(0x07)  # Command not supported
                self.sendall(self.request, reply)
                return

            resolved_address, resolved_port = self.resolve_addr_port(address, port)

            try:
                if self.server.proxy.isDown:
                    raise Exception("Proxy is down")

                remote = self.server.proxy.socket()
                remote.connect((resolved_address, resolved_port))
            except Exception as err:
                self.print(f"Could not connect to remote: {err}")
                reply = self.generate_failed_reply(0x05)  # Connection refused
                self.sendall(self.request, reply)
                return

            self.print(f"Connected to {resolved_address}:{resolved_port}")

            bind_address = remote.getsockname()
            addr = struct.unpack("!I", socket.inet_aton(bind_address[0]))[0]
            port = bind_address[1]
            reply = struct.pack(
                "!BBBBIH", SOCKS_VERSION, 0, 0, SOCKS5_ATYPE_IPV4, addr, port
            )
            self.sendall(self.request, reply)

            if not self.exchange_loop(self.request, remote):
                raise ConnectionInterrupted("timed out")

        except ConnectionInterrupted as e:
            self.print(f"Connection interrupted: {e}")
            if self.server.proxy != None:
                self.server.proxy.restart()
        finally:
            self.server.close_request(self.request)
            self.print("Closed connection")


class Proxy:
    def __init__(self, address, restartCMD=None):
        self.address = address
        self.restartCMD = restartCMD

        self.host, self.port = address.replace("socks5://", "").rsplit(":", 1)
        self.port = int(self.port)

        self.proxies = {"http": self.address, "https": self.address}
        self.isDown = False

        # Start the server
        threading.Thread(target=self.start_server).start()

    def start_server(self):
        host, port = "0.0.0.0", self.port + 10000

        self.server = ThreadingTCPServer(("0.0.0.0", port), SocksProxy)
        self.server.proxy = self

        # Start server
        logger.info(f"Proxying {self.host}:{self.port} on {host}:{port}")
        self.server.serve_forever()

    def socket(self):
        socket = socks.socksocket()
        socket.set_proxy(socks.SOCKS5, self.host, self.port)

        return socket

    def restart(self):
        if self.isDown:
            return

        self.isDown = True
        logger.info(f"{self.host}:{self.port} is down")

        # Try restarting
        threading.Thread(target=self.try_restart).start()

    def try_restart(self):
        while True:

            # restart the proxy
            if self.restartCMD:
                logger.info(f"Restarting {self.host}:{self.port}...")

                result = subprocess.run(
                    self.restartCMD, shell=True, capture_output=True, text=True
                )

                if result.returncode != 0:
                    logger.error(
                        f"{self.host}:{self.port} failed to restart: {result.stderr}"
                    )

            # test is the proxy working
            if self.test():
                break

            # timeout
            time.sleep(10)

        self.isDown = False
        logger.info(f"{self.host}:{self.port} is up")

    def test_link(self, link):
        try:
            resp = requests.get(link, proxies=self.proxies)
            return str(resp.status_code)[0] == "2"
        except:
            return False

    def test(self):
        return False not in set(map(self.test_link, testLinks))


# Read config
with open("config.json", "r") as file:
    config = json.load(file)

# Set logging level
logging.basicConfig()
logger = logging.getLogger()
logger.handlers.clear()
logger_hdl = logging.StreamHandler()
logger_hdl.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(logger_hdl)

logLevel = logging.DEBUG if config.get("debug", False) else logging.INFO
logger.setLevel(logLevel)

# Timeouts settings
primaryTimeout = config.get("primaryTimeout", 10)
secondaryTimeout = config.get("secondaryTimeout", 1.5)

# Proxy settings
testLinks = config.get("testLinks", [])
for proxy in config.get("proxies", []):
    Proxy(proxy["address"], proxy.get("restartCMD", None))
