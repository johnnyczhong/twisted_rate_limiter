from twisted.protocols.basic import NetstringReceiver
import json
from twisted.python import log
import time

# actions specific to each protocol/connection
class RateLimiterProtocol(NetstringReceiver):
    """
    # may be handy later
    def connectionMade(self):
        self.factory.numProtocols += 1
    """

    def stringReceived(self, request):
        self.request = request.decode()
        self.process_request()
    
    def process_request(self):
        response = self.req()

        if type(response) is  dict:
            response = json.dumps(response) # encode dict as JSON string
            response = response.encode('utf-8') # encode JSON string as bytes object
            log.msg('returning {} bytes to calling application'.format(len(response)))

            self.sendString(response)
            self.transport.loseConnection()
        else:  # external or internal rate limited
            self.factory.delay = response
            from twisted.internet import reactor
            reactor.callLater(0, self.process_request,)

    """ 
    # may be handy later
    def connectionLost(self, reason):
        self.factory.numProtocols -= 1
    """

    def req(self):
        now = time.time()

        if now >= (1.2 + self.factory.last_token_time + self.factory.delay):
            # reset token distribution timer
            self.factory.last_token_time = now
            # reset delay timer
            self.factory.delay = 0
            try:
                resp = self.factory.service.make_request(self.request)
                return resp
            except:
                return 0 # request failed
        else:
            return 0
