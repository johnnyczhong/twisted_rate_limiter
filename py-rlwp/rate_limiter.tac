# import and append to path because twistd does not recognize
# current directory
import sys
sys.path.append('/home/ubuntu/py-rlwp/py-rlwp')

import rate_limiter_service
import rate_limiter_factory

from twisted.application import internet, service

# constants
PORT = 8001
IFACE = 'localhost'

# init service layers
top_service = service.MultiService()
proxy_service = rate_limiter_service.RequestService()

# init factory to process incoming requests
factory = rate_limiter_factory.RateLimiterFactory(proxy_service)
tcp_service = internet.TCPServer(PORT, factory, interface = IFACE)
tcp_service.setServiceParent(top_service)


# assign application variable and set services
application = service.Application('RateLimiterProxy')
top_service.setServiceParent(application)
