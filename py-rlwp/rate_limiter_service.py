from twisted.python import log
import requests
import json

# methods to make requests and handle each response
class RequestService():

    """
    url = None #cached request
    resp = None #cached response
    """

    def make_request(self, url):
        log.msg('request url: {}'.format(url))
        response = requests.get(url)
        action_code = self.parse_response_codes(response)
        if action_code > 0:
            return action_code
        else:
            return response.json()

    # purpose: get the response codes
    #   and figure out what to do with them?
    # returns: an int.
    #   -1: retry immediately (server error?)
    #    0: valid response (200 or 404)
    #   +n: retry after n seconds (rate limited, 1s+)
    def parse_response_codes(self, response):

        
        def get_rate_limit_type(self, headers):
            # if rate limited by user or service
            if 'X-Rate-Limit-Type' in headers:
                return headers['Retry-After']
            # if rate limited by underlying riot proxy
            else:
                return 1

        if response.status_code == 404:
            r = 0
        elif response.status_code == 200:
            r = 0
        elif response.status_code == 429: 
            # try again after the delay
            r = get_rate_limit_type(response.headers)
        elif response.status_code == 503:
            # try again after 1s
            r = 1
        elif response.status_code == 500:
            pass
        else:
            r = -1
        log.msg('status_code: {}'.format(response.status_code))
        return r

    

    # purpose: extract rate limit header
    # returns: [int(num_calls_10s), int(num_calls_600s)]
    def parse_rate_limit(self, response):
        num_calls, split1 = [], []
        split0 = response.headers['X-Rate-Limit-Count'].strip().split(',')
        for i in split0:
            split1.append(i.strip().split(':'))
        for i in split1:
            num_calls.append(i[0])
        num_calls = [int(x) for x in num_calls]
        return num_calls

