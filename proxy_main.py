from Proxy import Proxy
from CacheHandler import CacheHandler
import os

def main():
    proxy = Proxy()
    print('Main:: proxy program starts')
    CacheHandler.origin = os.getcwd()
    proxy.listenConnection()
    print('Main:: proxy program ends')


if __name__ == '__main__':
    main()
