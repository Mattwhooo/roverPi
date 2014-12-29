import tcp_connection
import RPi.GPIO as io


## Order Of Methods that can be Monkey Patched
#      - Setup - Configure all RPi GPIO.
#      - Run -  Retrieve Data From TCP Stream and Act on it.  Should contain a loop to continue running
#      - Cleanup - Close all GPIO Connections

left_label = 'RotationZ'
right_label = 'Y'


#Overwritting Default Setup Method
# - GPIO Setup
def setup(self):

    self.Motor1A = 4
    self.Motor1B = 17
    self.Motor1E = 22

    self.Motor2A = 18
    self.Motor2B = 23
    self.Motor2E = 25

    try:
        io.setmode(io.BCM)

        io.setup(self.Motor1A, io.OUT)
        io.setup(self.Motor1B, io.OUT)
        io.setup(self.Motor1E, io.OUT)
        io.setup(self.Motor2A, io.OUT)
        io.setup(self.Motor2B, io.OUT)
        io.setup(self.Motor2E, io.OUT)
        io.output(self.Motor1E, io.HIGH)
        io.output(self.Motor2E, io.HIGH)
        self.pw_left = io.PWM(self.Motor1E, 500)
        self.pw_right = io.PWM(self.Motor2E, 500)
        self.pw_left.start(0)
        self.pw_right.start(0)
    except:
        print "Error During IO Setup"


#Overwritting Default Cleanup Method
# - GPIO Cleanup
def cleanup(self):
    self.pw_left.stop()
    self.pw_right.stop()
    io.cleanup()


#Overwrite Default Run Method
# - Handles a single input from Control Stream
def run(self):
    data = self.server.recvfrom(1024)
    if data:
        self.parse_input(data)


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

tcp_connection.ControlStream.setup = setup
tcp_connection.ControlStream.run = run
tcp_connection.ControlStream.cleanup = cleanup
tcp_connection.ControlStream.forward = forward
tcp_connection.ControlStream.reverse = reverse
tcp_connection.ControlStream.parse_input = parse_input


if __name__ == '__main__':

    CS = tcp_connection.CommandStream(port=5001)

    while True:
        CS.open()
        cont = CS.run()
        if cont:
            pass
        else:
            CS.close()
            print 'Releasing Command Stream Connection'


