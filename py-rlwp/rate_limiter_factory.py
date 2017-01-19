from twisted.internet.protocol import ServerFactory
import time

import rate_limiter_protocol

# a state keeper
class RateLimiterFactory(ServerFactory):
    protocol = rate_limiter_protocol.RateLimiterProtocol

    def __init__(self, service):
        self.service = service
        # self.numProtocols = 0 # might come in handy
        self.curr_tokens_10 = 1 # 1/1s in test, 300/1s in prod
        self.last_token_time = time.time() # now
        self.delay = 0

    
