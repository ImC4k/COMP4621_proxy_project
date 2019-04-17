from Proxy import Proxy

def main():
    proxy = Proxy()
    print('Main:: proxy program starts')
    proxy.listenConnection()
    print('Main:: proxy program ends')


if __name__ == '__main__':
    main()
