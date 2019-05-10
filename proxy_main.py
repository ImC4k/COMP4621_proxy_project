from Proxy import Proxy
from CacheHandler import CacheHandler
import os
import sys

def main():
    max_connection = None
    port = None
    for option in sys.argv[1:]:
        optionName, val = option.split('=')
        if optionName == 'max_connection':
            max_connection = int(val)
        elif optionName == 'port':
            port = int(val)

    proxy = Proxy(max_connection=max_connection, port=port)
    print('Main:: proxy program starts')
    CacheHandler.origin = os.getcwd()
    proxy.listenConnection()
    print('Main:: proxy program ends')


if __name__ == '__main__':
    main()
