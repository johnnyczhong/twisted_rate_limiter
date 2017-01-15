#purpose: https web proxy with rate limiting
# run as a service that will intercept requests from junglr
# 1. the client (junglr) sends the riot api call via RPC (remote procedure call)
#    to this server, which initiates the request to riot's servers and
#    returns the response back to the client.
# 2. put request into rate limited queue
# 3. when not rate limited, proxy takes request and executes it through reactor
# 4. reactor returns full response to junglr.

# it seems like the twisted's Proxy module does not support https proxying.
# as a result, I've written an short application that, when a url
# is provided will execute the request on the behalf of the calling application

from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import NetstringReceiver
from twisted.application import internet, service
from twisted.python import log
import requests
import time
import json

DEBUG = True
RLC_HEADER = 'X-Rate-Limit-Count'
RATE_PER_10 = 10
RATE_PER_600 = 500

PORT = 8001
IFACE = 'localhost'


# purpose: performs the action desired
# in this case, makes an https request on the client's behalf.
# low context, performs simple operations to be determined by factory
class RequestService(service.Service):
    
    # purpose: make request to Riot's API
    # return: web response
    def make_request(self, url): 
        url = url.decode('utf-8')
        log.msg('request url: {}'.format(url))
        response = requests.get(url)
        return response.json()
    
    # TODO: extract status code from response
    def get_response_codes(self, response):
        if response.status_code == 404:
            msg = 'Not Found'
        elif response.status_code == 200:
            msg = 'Valid'
        elif (response.status_code == 429 or response.status_code == 503 
                or response.status_code == 500):
            msg = 'Retry'
        else:
            msg = 'Unknown Status Code'
        log.msg('msg: {}'.format(msg))
        return msg

    # TODO: extract rate limit header
    # returns: [int(num_calls_10s), int(num_calls_600s)]
    def parse_rate_limit(self, response):
        num_calls = []
        split1 = []
        split0 = response.headers[RLC_HEADER].strip().split(',')
        for i in split0:
            split1.append(i.strip().split(':'))
        for i in split1:
            num_calls.append(i[0])
        num_calls = [int(x) for x in num_calls]
        return num_calls

# purpose: represents one connection from client to proxy/this server.
# makes a call to a method stored by the factory.
# middle context, handles incoming connections and responds back
class RequestProtocol(NetstringReceiver):
    def connectionMade(self):
        self.factory.numProtocols += 1
        #print('Current number of protocols: {}'.format(self.factory.numProtocols))

    # parse string out of Netstring
    def stringReceived(self, request):
        url = str(request)
        self.process_request(request)
        
    def process_request(self, request):
        response = self.factory.req(request)
        if response is not None:
            response = json.dumps(response) # encode as JSON string
            response = response.encode('utf-8') # encode JSON string as bytes object

            log.msg('returning {} bytes to calling application'.format(len(response)))
            self.sendString(response) # send response to client as bytes/netstring
            self.transport.loseConnection()
        else: # attempt function again
            # send back a response that would tell the calling application
            # an expected timeout
            #self.sendString(timeout)
            wait_time = (self.factory.numProtocols 
                    - self.factory.curr_tokens_10) * (10/self.factory.tokens_per_10)
            reactor.callLater(0,
                    self.process_request, request)

    def connectionLost(self, reason):
        self.factory.numProtocols -= 1

# purpose: creates instances of protocols in response to connections
# keep rate limits here
# high context, creates protocols to handle incoming connections
# determines what actions to take based on current conditions
class RequestFactory(ServerFactory):
    protocol = RequestProtocol

    def __init__(self, service):
        self.service = service
        self.numProtocols = 0
        self.curr_tokens_10 = 1
        self.last_token_time = time.time() # now
        self.tokens_per_10 = 10 # num requests allowed per 10s

    
    # move this to protocol?
    def req(self, url):
        # TODO: hybrid rate limit check between Riot Api and own rate limiter
        now = time.time()

        # refresh timer of 1.2s. restore token count and update last token distribution time
        if now >= (1.2 + self.last_token_time):
            self.last_token_time = now
            try:
                resp = self.service.make_request(url) # make request to Riot
                #resp = self.service.startService(url)
                return resp
            except:
                return None # request failed
        else:
            return None


# === TAC FILE STARTS HERE ===
# start services
top_service = service.MultiService()
proxy_service = RequestService()

# init tcp service to listen to port
# this uses the factory I've created to process incoming requests
factory = RequestFactory(proxy_service)
tcp_service = internet.TCPServer(PORT, factory, interface = IFACE)
tcp_service.setServiceParent(top_service)

# assign application variable and set services
application = service.Application('TestProxy')
top_service.setServiceParent(application)


# === TAC FILE STOPS HERE === 

# testing
def main():
    service = RequestService()
    main_service = service.MultiService()

    factory = RequestFactory(service)
    reactor.listenTCP(8001, factory)
    reactor.run()

if __name__ == '__main__':
    main()
