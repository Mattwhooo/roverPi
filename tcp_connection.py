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
    left_label = 'Y'
    right_label = 'Z'

    def __init__(self, host, port, size=1024, backlog=5):
        super(ControlStream, self).__init__(host, port, size, backlog)
        GPIO.setmode(GPIO.BCM)

        Motor1A = 4
        Motor1B = 17
        Motor1E = 22

        Motor2A = 18
        Motor2B = 23
        Motor2E = 25

        io.setup(Motor1A, io.OUT)
        io.setup(Motor1B, io.OUT)
        io.setup(Motor1E, io.OUT)
        io.setup(Motor2A, io.OUT)
        io.setup(Motor2B, io.OUT)
        io.setup(Motor2E, io.OUT)
        io.output(Motor1E, io.HIGH)
        io.output(Motor2E, io.HIGH)

        self.pw_left = io.PWM(Motor1E, 0)
        self.pw_right = io.PWM(Motor2E, 0)
        self.pw_left.start(0)
        self.pw_right.start(0)


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

    def forward(self, side):
        if side == 'left':
            io.output(Motor2A, io.HIGH)
            io.output(Motor2B, io.LOW)
        else:
            io.output(Motor1A, io.HIGH)
            io.output(Motor1B, io.LOW)

    def reverse(self, side):
        if side == 'left':
            io.output(Motor2A, io.LOW)
            io.output(Motor2B, io.HIGH)
        else:
            io.output(Motor1A, io.LOW)
            io.output(Motor1B, io.HIGH)

    def parse_input(self, data):
        left = data.find(self.left_label)
        right = data.find(self.right_label)
        if left != -1:
            left_value = int(data[data.find(':', left)+1:data.find('~', left)]) - 90
            if left_value > 5:
                self.forward('left')
                self.pw_left.ChangeDutyCycle(left_value)
            elif left_value < -5:
                self.reverse('left')
                self.pw_left.ChangeDutyCycle(left_value)
            else:
                self.pw_left.ChangeDutyCycle(0)
        if right != -1:
            right_value = int(data[data.find(':', right)+1:data.find('~', right)]) - 90
            if left_value > 5:
                self.forward('right')
                self.pw_left.ChangeDutyCycle(right_value)
            elif left_value < -5:
                self.reverse('right')
                self.pw_left.ChangeDutyCycle(right_value)
            else:
                self.pw_left.ChangeDutyCycle(0)


    def run(self):
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
    CS = CommandStream(ip, 5000)

    while True:
        CS.open()
        cont = CS.run()
        if cont:
            pass
        else:
            CS.close()
            print 'Releasing Command Stream Connection'

