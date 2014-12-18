import threading
import socket
import os



class TCPStream(object):
    type = 'tcp'
    def __init__(self, host, port, size=1024, backlog=5):
        self.host = host
        self.port = port
        self.size = size
        self.backlog = backlog

        if self.type == 'tcp':
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(200)
        if self.type == 'udp':
            self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server.bind(('', self.port))

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
                    self.control = cntrls
                    self.client.send(str(self.host) + ':' + str(self.port + 1))
                    cntrls.open()
                    print('Control Stream Loaded!')
                elif data == '<GAMEPADKILL>':
                    self.control.stop_thread()
                elif data == '<VIDEOINFO>':
                    print('Attempting to Open Video Stream')
                    self.client.send(str(self.host) + ':' + str(self.port + 2))
                    self.video = VideoStream(self.host, self.port + 2)
                    self.video.run()
                    print('Video Stream Open')
                elif data =='<VIDEOKILL>':
                    self.video.stop_video()
                else:
                    self.client.send('...')


class VideoStream(TCPStream):
    type = 'video'
    def run(self):
        thread = threading.Thread(target=self.start_video, args=())
        thread.daemon = True
        thread.start()
        self.thread = thread

    def start_video(self):
        os.system('raspivid -t 0 -h 180 -w 270 -fps 25 -hf -b 2000000 -o - | gst-launch-1.0 -v fdsrc ! h264parse !  rtph264pay config-interval=1 pt=96 ! gdppay ! tcpserversink host=' + self.host + ' port=' + str(self.port))

    def stop_video(self):
        print 'Attempting to Kill Video Stream'
        os.system('pkill raspivid')
        print 'Video Stream Killed'


class ControlStream(TCPStream):
    type = 'udp'

    def open(self):
        print ('Opening Control Stream...')
        self.stop = False
        #super(ControlStream, self).open()
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def stop_thread(self):
        self.stop = True
        self.server.close()

    def run(self):
        self.server.settimeout(1)
        while True:
            try:
                data, addr = self.server.recvfrom(1024)
                print 'Control-Stream: ',  data
            except:
                pass

            if self.stop:
                break
        print 'Exit GamePad Thread'

if __name__ =='__main__':

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com",80))
    ip = s.getsockname()[0]
    s.close()
    CS = CommandStream(ip, 5002)

    while True:
        CS.open()
        cont = CS.run()
        if cont:
            pass
        else:
            CS.close()
            print 'Releasing Command Stream Connection'

