import threading
import socket
import os


#Class TCPStream - Parent class that all TCPStream types inherit from
# - Can be TCP or UPD type as indicated by class variable
# - If not provided in the constructor the IP address will be automatically found
#    - This can be lead to unexpected behavior when trying to communicate over different networks
class TCPStream(object):

    #Class Variable Type - Controls what kind of socket should be opened
    # - Defaults to TCP
    type = 'tcp'

    #Handles Binding of Socket
    # - Will automatically get local IP address if no IP is provided
    # - Will automatically find open port if no port is provided
    # - Will Create either TCP or UDP Socket depending on type class variable
    def __init__(self, host='default', port=0, size=1024, backlog=5):
        if host == 'default':
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("gmail.com",80))
            self.host = s.getsockname()[0]
            s.close()
        else:
            self.host = host
        if port == 0:
            self.port = self.get_open_port()
        else:
            self.port = port
        self.size = size
        self.backlog = backlog

        if self.type == 'tcp':
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.port = self.server.getsockname()[1]
            self.server.listen(200)
        if self.type == 'udp':
            self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server.bind(('', self.port))
            self.port = self.server.getsockname()[1]

    # Method Open - Responsible for waiting for connection from client
    def open(self):
        print ('Waiting For Stream Connection...')
        self.client, self.address = self.server.accept()
        print 'Connected to Client: Ip-' + str(self.address)

    # Method Close - Shutdown server safely to prevent locking socket
    def close(self):
        self.server.shutdown(1)

    # Method Get Open Port - Used to a port that is open to use for Control and Video Streams
    def get_open_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        port = s.getsockname()[1]
        s.close()
        return port

#Class CommandStream - Handles Commands from the Client.
# - Creates Control and Video stream on demand
# - Responsible for closing streams
class CommandStream(TCPStream):

    #Method Run - Main Program Method.
    # - Loops through listening for commands from Client
    # - Commands can create or destroy other streams for data
    def run(self):

        while True:
            data = self.client.recv(1024)
            if data:

                print 'Command-Stream: ' + data
                if data == '<SERVERKILLCONNECTION>':
                    self.client.send('<DISCONNECTING>')
                    return False
                elif data == '<GAMEPADINFO>':
                    self.control = ControlStream(self.host)
                    self.client.send(str(self.host) + ':' + str(self.control.port))
                    self.control.open()
                    print('Control Stream Loaded!')
                elif data == '<GAMEPADKILL>':
                    self.control.stop_thread()
                    self.client.send('<GAMEPADKILL-OK>')
                elif data == '<VIDEOINFO>':
                    print('Attempting to Open Video Stream')
                    self.video = VideoStream(self.host)
                    self.client.send(str(self.host) + ':' + str(self.video.port))
                    self.video.run()
                    print('Video Stream Open')
                elif data =='<VIDEOKILL>':
                    self.video.stop_video()
                    self.client.send('<VIDEOKILL-OK>')
                else:
                    self.client.send('...')

#Class VideoStream - Stream responsible for handling video stream from Raspberry Pi Camera
# - Uses GStreamer
class VideoStream(TCPStream):

    #Setting Type to Video prevents Socket Binding
    type = 'video'

    #Runs Video Stream in separate thread to prevent blocking
    def run(self):
        thread = threading.Thread(target=self.start_video, args=())
        thread.daemon = True
        thread.start()
        self.thread = thread

    #Start Video Stream
    def start_video(self):
        os.system('raspivid -t 0 -h 360 -w 648 -fps 40 -hf -b 2000000 -o - | gst-launch-1.0 -v fdsrc ! h264parse !  rtph264pay config-interval=1 pt=96 ! gdppay ! tcpserversink host=' + self.host + ' port=' + str(self.port))

    #Stop Video Stream by killing off Raspivid process.  This causes GStreamer to Exit gracefully because stream ended
    def stop_video(self):
        print 'Attempting to Kill Video Stream'
        os.system('pkill raspivid')
        print 'Video Stream Killed'

#Class ControlStream - Stream responsible for handling data from controller
# - Features methods that can be monkey patched to support multiple projects
# - Methods run in the following order Setup, Run, Cleanup
# - Run will be called continuously until CommandStream gets request to close ControlStream
class ControlStream(TCPStream):
    type = 'udp'
    left_label = 'RotationZ'
    right_label = 'Y'

    #Calls Setup after Init for Monkey Patching GPIO Data by project
    def __init__(self, host='default', port=0, size=1024, backlog=5):
        super(ControlStream, self).__init__(host, port, size, backlog)
        self.stop = False
        self.timeout = 1
        self.setup()

    #Method Setup - Allows Monkey Patching for initializing GPIO setup by project
    # - This method is expected to be overwritten for most projects
    def setup(self):
        pass

    #Method Open - Waits for Control Stream to Open
    def open(self):
        print ('Opening Control Stream...')
        self.stop = False
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    #Method Stop Thread - Kills the Control Stream run thread
    def stop_thread(self):
        self.cleanup()
        self.stop = True
        self.server.close()

    #Method Cleanup - is called before Run Thread is stopped to allow GPIO cleanup
    # - This method is expected to be overwritten for most projects
    def cleanup(self):
        pass

    #Method Run Loop - Main Program Loop for Control Stream
    # - Continuously runs Run Method and checks for Server.Stop
    def run_loop(self):
        self.server.settimeout(self.timeout)
        while True:
            try:
                self.run()
            except:
                if self.stop:
                    break

    #Method Run - Handles a single input to the Control Stream
    # - Called by Run Loop Method continuously until Server stop command received
    # - This method is expected to be overwritten for most projects
    def run(self):
        data, addr = self.server.recvfrom(1024)
        if data:
            print data


if __name__ == '__main__':

    CS = CommandStream(port=5001)

    while True:
        CS.open()
        cont = CS.run()
        if cont:
            pass
        else:
            CS.close()
            print 'Releasing Command Stream Connection'

