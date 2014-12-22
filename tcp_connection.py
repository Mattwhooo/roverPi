import threading
import socket
import os
import RPi.GPIO as io
from time import sleep


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
                    self.client.send('<GAMEPADKILL-OK>')
                elif data == '<VIDEOINFO>':
                    print('Attempting to Open Video Stream')
                    self.client.send(str(self.host) + ':' + str(self.port + 2))
                    self.video = VideoStream(self.host, self.port + 2)
                    self.video.run()
                    print('Video Stream Open')
                elif data =='<VIDEOKILL>':
                    self.video.stop_video()
                    self.client.send('<VIDEOKILL-OK>')
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
        os.system('raspivid -t 0 -h 360 -w 648 -fps 40 -hf -b 2000000 -o - | gst-launch-1.0 -v fdsrc ! h264parse !  rtph264pay config-interval=1 pt=96 ! gdppay ! tcpserversink host=' + self.host + ' port=' + str(self.port))

    def stop_video(self):
        print 'Attempting to Kill Video Stream'
        os.system('pkill raspivid')
        print 'Video Stream Killed'


class ControlStream(TCPStream):
    type = 'udp'
    left_label = 'RotationZ'
    right_label = 'Y'

    def __init__(self, host, port, size=1024, backlog=5):
        super(ControlStream, self).__init__(host, port, size, backlog)
        io.setmode(io.BCM)

        self.Motor1A = 4
        self.Motor1B = 17
        self.Motor1E = 22

        self.Motor2A = 18
        self.Motor2B = 23
        self.Motor2E = 25

        io.setup(self.Motor1A, io.OUT)
        io.setup(self.Motor1B, io.OUT)
        io.setup(self.Motor1E, io.OUT)
        io.setup(self.Motor2A, io.OUT)
        io.setup(self.Motor2B, io.OUT)
        io.setup(self.Motor2E, io.OUT)
        io.output(self.Motor1E, io.HIGH)
        io.output(self.Motor2E, io.HIGH)


    def open(self):
        print ('Opening Control Stream...')
        self.stop = False
        #super(ControlStream, self).open()
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def stop_thread(self):
        self.pw_left.stop()
        self.pw_right.stop()
        io.cleanup()
        self.stop = True
        self.server.close()

    def reverse(self, side):
        if side == 'right':
            io.output(self.Motor2A, True)
            io.output(self.Motor2B, False)
        else:
            io.output(self.Motor1A, True)
            io.output(self.Motor1B, False)

    def forward(self, side):
        if side == 'right':
            io.output(self.Motor2A, False)
            io.output(self.Motor2B, True)
        else:
            io.output(self.Motor1A, False)
            io.output(self.Motor1B, True)

    def parse_input(self, data):
        left = data.find(self.left_label)
        right = data.find(self.right_label)
        if left != -1:
            left_value = int(data[data.find(':', left)+1 :data.find('~', left)])-90
            if left_value > 5:
                self.forward('left')
                self.pw_left.ChangeDutyCycle(abs(left_value))
                print('Left Duty Cycle: ' + str(abs(left_value)))
            elif left_value < -5:
                self.reverse('left')
                self.pw_left.ChangeDutyCycle(abs(left_value))
                print('Left Duty Cycle: ' + str(abs(left_value)))
            else:
                self.pw_left.ChangeDutyCycle(0)
                print('Left Duty Cycle: 0')
        if right != -1:
            right_value = int(data[data.find(':', right)+1:data.find('~',right)]) - 90
            print str(right_value)
            if right_value > 5:
                self.forward('right')
                self.pw_right.ChangeDutyCycle(abs(right_value))
                print('Right Duty Cycle: ' + str(abs(right_value)))
            elif right_value < -5:
                self.reverse('right')
                self.pw_right.ChangeDutyCycle(abs(right_value))
                print('Right Duty Cycle: ' + str(abs(right_value)))
            else:
                self.pw_right.ChangeDutyCycle(0)
                print('Right Duty Cycle: 0')


    def run(self):
        self.pw_left = io.PWM(self.Motor1E, 500)
        self.pw_right = io.PWM(self.Motor2E, 500)
        self.pw_left.start(0)
        self.pw_right.start(0)

        self.server.settimeout(1)
        while True:
            try:
                data, addr = self.server.recvfrom(1024)
                if data:
                    self.parse_input(data)

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
    CS = CommandStream(ip, 5020)

    while True:
        CS.open()
        cont = CS.run()
        if cont:
            pass
        else:
            CS.close()
            print 'Releasing Command Stream Connection'

