import threading
import socket



class TCPStream(object):

    def __init__(self, host, port, size=1024, backlog=5):
        self.host = host
        self.port = port
        self.size = size
        self.backlog = backlog
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(200)

    def open(self):
        print ('Waiting For Stream Connection...')
        self.client, self.address = self.server.accept()
        print 'Connected to Client: Ip-' + str(self.address)

    def close(self):
        self.server.shutdown(1)

class CommandStream(TCPStream):

    def run(self):

        while True:
            data = self.client.recv(1024)
            if data:

                print 'Command-Stream: ' + data
                if data == '<SERVERKILLCONNECTION>':
                    self.client.send('<DISCONNECTING>')
                    return False
                elif data == '<GAMEPADINFO>':
                    cntrls = ControlStream(self.host, self.port + 1)
                    self.client.send(str(self.host) + ':' + str(self.port + 1))
                    cntrls.open()
                    print('Control Stream Loaded!')
                else:
                    self.client.send('...')

class ControlStream(TCPStream):
    def __init__(self, host, port, size=1024, backlog=5):
        super(ControlStream, self).__init__(host, port, size, backlog)
        self.server = self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def open(self):
        print ('Opening Control Stream...')
        #super(ControlStream, self).open()
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):

        while True:
            data = self.server.recvfrom(1024)
            if data:
                print 'Control-Stream: ' + data

if __name__ =='__main__':
    CS = CommandStream('192.168.1.144', 5000, 1024, 5)
    while True:
        CS.open()
        cont = CS.run()
        if cont:
            pass
            print 'cont'
        else:
            CS.close()
            print 'exit1'

