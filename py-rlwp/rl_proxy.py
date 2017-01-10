#!/home/ubuntu/venv/bin/python

import socket, sys
#from threading import *
import threading

try:
    listen_to = int(input("[*] Enter listening port number: "))
except KeyboardInterrupt:
    print("\n[*] User requested interrupt" )
    print("[*] Application exiting... ")
    sys.exit()

MAX_CONN = 10 # max number of connections queue will hold
BUFFER_SIZE = 4096 # max byes of transmission
DEBUG = True



def start():
    try:
        print("[*] Initializing sockets...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # init socket
        s.bind(('', listen_to)) # bind socket to be listened to
        s.listen(MAX_CONN) # start listening to incoming connections
        print("[*] Done.")
        print("[*] Sockets bound successfully... ")
        print("[*] Server started for {}\n".format(listen_to))
    except Exception as e:
        # error out if any socket methods fail
        print("[*] Unable to initialize socket: {}".format(e))
        sys.exit(2)

    while True: # continuous loop here?
        try:
            conn, addr = s.accept() # accept connection from client (change this?)
            data = conn.recv(BUFFER_SIZE) # receive client data
            
            if DEBUG:
                print('[*] Connection: {}'.format(conn))
                print('[*] Data: {}'.format(data))
                print('[*] Address: {}'.format(addr))

            #TODO: insert rate limiter functionality here
            threading.Thread(target = conn_string, args = (conn, data, addr)) # starts a thread that makes the connection
        except KeyboardInterrupt:
            # execute if client socket connection fails
            s.close()
            print("\n[*] User submitted stop. Proxy server shutting down.")
            sys.exit(1)
        except Exception as e:
            print(e)

    s.close()

# parses the connection string to something that proxy_server can understand
# need to have the web proxy understand the request
def conn_string(conn, data, addr): # do I need this?
    # client browser request appears here
    try:
        first_line = data.split('\n')[0]
        url = first_line.split(' ')[1]
        http_pos = url.find('://') #find position of ://

        if http_pos == -1:
            temp = url
        else:
            temp = url[http_pos+3:] #get rest of the url

        port_pos = temp.find(':') # find the position of the port (if any)
        webserver_pos = temp.find('/') # find end of webserver name, first slash after http://
        
        if webserver_pos == -1: # if no ending slash, then length is equal to request
            webserver_pos = len(temp)

        webserver = ''
        port = -1 # terminal value

        if port_pos == -1 or webserver_pos < port_pos: #default port (80)
            port = 443 
            webserver = temp[:webserver_pos]
        else:
            #specific port
            port = int(temp[port_pos + 1:][:webserver_pos - port_pos - 1]) #
            webserver = temp[:port_pos]

        print('passing to proxy_server')
        proxy_server(webserver, port, conn, addr, data)
    except Exception as e:
        print("\n[*] Connection string attempted: {}".format(e))
        pass


# proxy server that will peform the request and return a response
def proxy_server(webserver, port, conn, data, addr):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((webserver, port,))
        s.send(data)

        while True:
            #read reply or data to and from webserver
            reply = s.recv(BUFFER_SIZE)

            if len(reply) > 0:
                conn.send(reply) #send reply back to client
                # send notification to proxy server [this service]
                dar = float(len(reply))
                dar = float(dar/1024)
                dar = '%.3s' % (str(dar))
                dar = '%s KB' % (dar)
                # request return message
                print('[*] Request Done: {} => {} <='.format(str(addr[0]), str(dar)))
            else:
                # break connection if receiving data failed
                break

        print('closing connections')
        # close server sockets after done (might not want to do it this way)
        s.close()

        # after everything is sent, close client socket (want to keep open, probably)
        conn.close()
    except socket.error as message:
        s.close()
        conn.close()
        print(message)
        sys.exit(1)

if __name__ == '__main__':
    start()

