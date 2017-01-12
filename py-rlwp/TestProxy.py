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
import requests
import time
import json

DEBUG = True
RLC_HEADER = 'X-Rate-Limit-Count'
RATE_PER_10 = 10
RATE_PER_600 = 500

# purpose: performs the action desired
# in this case, makes an https request on the client's behalf.
# low context, performs simple operations to be determined by factory
class RequestService():
    # purpose: make request to Riot's API
    # return: web response
    def make_request(self, url): 
        url = url.decode('utf-8')
        #response = requests.get(url)
        #return response
        return url
    
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
        print('msg: {}'.format(msg))
        return msg

    # TODO: extract rate limit header
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

            self.sendString(response) # send response to client as bytes/netstring
            self.transport.loseConnection()
        else: # attempt function again
            #self.sendString(timeout)
            wait_time = (self.factory.numProtocols 
                    - self.factory.curr_tokens_10) * (10/self.factory.tokens_per_10)
            print('waiting for {}'.format(wait_time))
            reactor.callLater(self.factory.numProtocols, 
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
        self.curr_tokens_10 = 10
        self.last_token_time = time.time() # now
        #self.tokens_10_minimum_refresh = 1
        self.tokens_per_10 = 10 # num requests allowed per 10s


    def req(self, url):
        # TODO: rate limit check here
        # this version of the check freezes due to an infinite loop
        # have to reset the counter somehow.
        # drip rate/burst rate?
        """
        if self.rate_limit_calls_per_10 >= (RATE_PER_10-1): # 9/10
            time.sleep(1) # stop for 1s
            return self.req(url) # try again
        elif self.rate_limit_calls_per_600 >= (RATE_PER_600 - 50): #350/500
            time.sleep(30) # stop for 30s
            return self.req(url) # try again
        """
        # check how many tokens we have, replenish if possible
        # if the current time is after minimum drip time
        # drip the appropriate number of tokens
        # if 1 second has elapsed since last token was distributed
        now = time.time()
        #print(self.last_token_time)
        if now >= 1 + self.last_token_time:
            #tokens = int(self.tokens_per_10 * ((time.time() - self.last_token_time)/10))
            # num of tokens dripped = seconds passed since last tokens dripped
            # not to exceed 10
            tokens = int(time.time() - self.last_token_time)
            tokens = 10 if (tokens > 10) else tokens # redundant?
            #print('New token count: {} at {}'.format(tokens, now))
            self.curr_tokens_10 += tokens
            self.curr_tokens_10 = 10 if (self.curr_tokens_10 > 10) else self.curr_tokens_10
            self.last_token_time = now
        # if we don't have tokens, have reactor come back at next token refresh time.
        if self.curr_tokens_10 <= 1:
            #reactor.callLater(1, self.req, url)
            return None
        else:
            #print('Subtracting a token from: {}'.format(self.curr_tokens_10))
            self.curr_tokens_10 -= 1
            #print('Current token count: {}'.format(self.curr_tokens_10))
            try:
                resp = self.service.make_request(url) # make request to Riot
                return resp
            except:
                return None # request failed
def main():
    service = RequestService()
    factory = RequestFactory(service)
    reactor.listenTCP(8001, factory)
    reactor.run()

if __name__ == '__main__':
    main()
