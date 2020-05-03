import sys
import argparse
import serial
from serial.tools import list_ports
import io
from PyQt5 import QtWidgets, uic, QtCore


class SignalGenerator:
    def __init__(self):
        # Serial things
        self.com_port = None
        self.connected = False
        self.serial = None
        self.serial_io = None
        self.serial_recv_line = None
        self.serial_user_data = []
        self.serial_rf_data = []
        self.serial_log_data = []

        # Argparse
        self.parser = None
        self.user_input = []
        self.args = None

        # Command line args
        self.mode = "generator"
        self.frequency = 25
        self.power = 0
        self.sweep_start = 25
        self.sweep_stop = 100
        self.sweep_steps = 100
        self.sweep_time = 5
        self.led_display = "kitt"
        self.rf_enabled = False
        self.updated = False

    def find_serial(self):
        """ Find a Signal Generator """

        # Find which COM port it is connected to
        ports = list_ports.comports()
        if ports != []:
            for port, desc, hwid in sorted(ports):
                # print("{}: {} [{}]".format(port, desc, hwid))
                if desc == "RF Signal Generator":
                    self.com_port = port

        if self.com_port == False:
            print("Signal Generator not found!")
        else:
            print("Signal Generator found on port: {}".format(self.com_port))

    def connect_serial(self, com_port=None):
        """ Connect to a Signal Generator """

        # Connect to given COM port
        if com_port is not None:
            self.com_port = com_port

        try:
            self.serial = serial.Serial(self.com_port, 115200, timeout=0.1)
            self.serial_io = io.TextIOWrapper(
                io.BufferedRWPair(self.serial, self.serial))

            self.send_data("WHOAMI")
            self.serial_io.flush()
            self.serial_recv_line = self.serial_io.readline().rstrip().lstrip("> ")

            # Confirm WHOAMI is correct
            if self.serial_recv_line == "Josh's Signal Generator!":
                print("Connected to {}".format(self.serial_recv_line))
                self.connected = True
        except:
            print("Could not connect.")

    def connect(self, com_port=None):
        """ Finds and Connects to Signal Generator """
        if self.com_port == None:
            self.find_serial()
        self.connect_serial(com_port)

    def send_data(self, data):
        """ Sends data to Signal Generator """
        self.serial_io.write(data + "\r\n")
        self.serial_io.flush()

    def get_data(self, type=None, single_line=False):
        """ Gets multiple user directed lines from Signal Generator, until timeout is hit """

        global meas_freq
        global meas_power

        self.serial_user_data = []
        self.serial_rf_data = []

        raw_recv = self.serial_io.readline()

        # only read a single line
        if single_line:
            return raw_recv.rstrip()

        while (raw_recv != ""):
            gui.processEvents()

            if raw_recv[0] == ">":
                self.serial_user_data.append(raw_recv.rstrip())
                if type == "user":
                    print(self.serial_user_data[-1])
            if raw_recv[0] == "+":
                self.serial_log_data.append(raw_recv.rstrip())
                if type == "log":
                    print(self.serial_log_data[-1])
            if raw_recv[0] == "?":
                # Send data for updating display
                meas_freq = raw_recv.split(" ")[1]
                meas_power = raw_recv.split(" ")[2]

                self.serial_rf_data.append(raw_recv.rstrip())
                if type == "rf":
                    print(self.serial_rf_data[-1])

            raw_recv = self.serial_io.readline()

        if type == "user":
            return self.serial_user_data
        if type == "log":
            return self.serial_log_data
        if type == "rf":
            return self.serial_log_data

    def talk(self):
        """ Transparently opens a COM port between user and Signal Generator """

        if not self.connected:
            self.connect()

        if self.connected:
            while True:
                user_input = input()
                if user_input.lower == "exit":
                    break
                self.send_data(user_input)
                self.get_data()
                [print(line) for line in self.serial_user_data]

    def config_sig_gen(self, frequency=None, power=None):
        if frequency is None:
            frequency = self.frequency
        if power is None:
            power = self.power

        self.send_data("sigGen({},{})".format(frequency, power))

    def config_sweep(self, start_freq=None, stop_freq=None, power=None, sweep_steps=None, time=None):
        if start_freq is None:
            start_freq = self.sweep_start
        if stop_freq is None:
            stop_freq = self.sweep_stop
        if power is None:
            power = self.power
        if sweep_steps is None:
            sweep_steps = self.sweep_steps
        if time is None:
            time = self.sweep_time

        self.send_data("sweep({},{},{},{},{})".format(
            start_freq, stop_freq, sweep_steps, power, time))

    def config_RF(self, enabled=False):
        if enabled:
            self.rf_enabled = True
            self.send_data("enableRF")
        else:
            self.rf_enabled = False
            self.send_data("disableRF")

    def config_leds(self, led_display=None):
        available_displays = ["kitt", "binary", "rainbow"]

        if led_display == "off":
            self.send_data("led 0")
        else:
            if led_display in available_displays:
                self.send_data("{}".format(led_display))
            else:
                print("LED option not found.")

    def parse_inputs(self, user_input):

        self.parser = argparse.ArgumentParser(
            description="Controls RF Signal Generator")

        self.parser.add_argument("-m", "--mode",        type=str,   dest="mode",
                                 help="select mode ([g]enerator, s[w]eep)")
        self.parser.add_argument("-f", "--frequency",   type=float, dest="frequency",
                                 help="frequency for signal generator in MHz")
        self.parser.add_argument("-p", "--power",       type=float, dest="power",
                                 help="output power in dBm")
        self.parser.add_argument("-a", "--start",       type=float, dest="start_freq",
                                 help="start frequency for sweep in MHz")
        self.parser.add_argument("-o", "--stop",        type=float, dest="stop_freq",
                                 help="stop frequency for sweep in MHz")
        self.parser.add_argument("-s", "--steps",       type=int,   dest="steps",
                                 help="number of steps in sweep")
        self.parser.add_argument("-t", "--time",        type=float, dest="time",
                                 help="time to sweep frequencies in seconds")
        self.parser.add_argument("-l", "--led",         type=str,   dest="led",
                                 help="led display (kitt, rainbow, binary)")
        self.parser.add_argument("-r", "--rf",          type=int,   dest="rf_enabled",
                                 help="rf enabled (1, 0)")

        # parse all the vars
        self.user_input = []
        [self.user_input.append(arg) for arg in user_input.split(" ")]
        self.args = self.parser.parse_args(self.user_input)

        # determine generator or sweep mode
        if self.args.mode == "g":
            self.mode = "generator"
        elif self.args.mode == "w":
            self.mode = "sweep"

        # store args in variables
        if self.args.frequency is not None:
            self.frequency = self.args.frequency

        if self.args.power is not None:
            self.power = self.args.power

        if self.args.start_freq is not None:
            self.sweep_start = self.args.start_freq

        if self.args.stop_freq is not None:
            self.sweep_stop = self.args.stop_freq

        if self.args.steps is not None:
            self.sweep_steps = self.args.steps

        if self.args.time is not None:
            self.sweep_time = self.args.time

        if self.args.led is not None:
            self.updated = "led"
            self.led_display = self.args.led

        if self.args.rf_enabled is not None:
            self.updated = "rf"
            if self.args.rf_enabled == 1:
                self.rf_enabled = True
            elif self.args.rf_enabled == 0:
                self.rf_enabled = False

        self.send_commands()

    def send_commands(self):
        if self.updated == "rf":
            self.config_RF(self.rf_enabled)
        elif self.updated == "led":
            self.config_leds(self.led_display)
        elif self.mode == "generator" and self.rf_enabled:
            self.config_sig_gen()
        elif self.mode == "sweep" and self.rf_enabled:
            self.config_sweep()

        self.get_data(type=None, single_line=False)
        self.updated = False


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        # Call the inherited classes __init__ method
        super(Ui, self).__init__()
        uic.loadUi('siggen_gui.ui', self)  # Load the .ui file

        # Buttons
        self.input_mode_single = self.findChild(
            QtWidgets.QRadioButton, "input_mode_single")
        self.input_mode_single.clicked.connect(
            lambda: sig_gen.parse_inputs("--mode g"))

        self.input_mode_sweep = self.findChild(
            QtWidgets.QRadioButton, "input_mode_sweep")
        self.input_mode_sweep.clicked.connect(
            lambda: sig_gen.parse_inputs("--mode w"))

        self.input_rf_enabled = self.findChild(
            QtWidgets.QCheckBox, "input_rf_enabled")
        self.input_rf_enabled.clicked.connect(
            lambda: sig_gen.parse_inputs("--rf {}".format(self.enable_rf())))

        # Inputs
        self.input_led_mode = self.findChild(
            QtWidgets.QComboBox, "input_led_mode")
        self.input_led_mode.currentTextChanged.connect(lambda: sig_gen.parse_inputs(
            "--led {}".format(self.input_led_mode.currentText().lower())))

        # Signal Generator
        self.input_siggen_freq = self.findChild(
            QtWidgets.QDoubleSpinBox, "input_siggen_freq")
        self.input_siggen_freq.valueChanged.connect(lambda: sig_gen.parse_inputs(
            "--frequency {:.3f}".format(self.input_siggen_freq.value())))

        self.input_siggen_power = self.findChild(
            QtWidgets.QDoubleSpinBox, "input_siggen_power")
        self.input_siggen_power.valueChanged.connect(lambda: sig_gen.parse_inputs(
            "--power {:.1f}".format(self.input_siggen_power.value())))

        # Sweep
        self.input_sweep_start = self.findChild(
            QtWidgets.QDoubleSpinBox, "input_sweep_start")
        self.input_sweep_start.valueChanged.connect(lambda: sig_gen.parse_inputs(
            "--start {:.3f}".format(self.input_sweep_start.value())))

        self.input_sweep_steps = self.findChild(
            QtWidgets.QDoubleSpinBox, "input_sweep_steps")
        self.input_sweep_steps.valueChanged.connect(lambda: sig_gen.parse_inputs(
            "--steps {:.0f}".format(self.input_sweep_steps.value())))

        self.input_sweep_power = self.findChild(
            QtWidgets.QDoubleSpinBox, "input_sweep_power")
        self.input_sweep_power.valueChanged.connect(lambda: sig_gen.parse_inputs(
            "--power {:.1f}".format(self.input_sweep_power.value())))

        self.input_sweep_stop = self.findChild(
            QtWidgets.QDoubleSpinBox, "input_sweep_stop")
        self.input_sweep_stop.valueChanged.connect(lambda: sig_gen.parse_inputs(
            "--stop {:.3f}".format(self.input_sweep_stop.value())))

        self.input_sweep_time = self.findChild(
            QtWidgets.QDoubleSpinBox, "input_sweep_time")
        self.input_sweep_time.valueChanged.connect(lambda: sig_gen.parse_inputs(
            "--time {:.0f}".format(self.input_sweep_time.value())))

        # Outputs
        self.output_siggen_freq = self.findChild(
            QtWidgets.QLCDNumber, "output_siggen_freq")
        self.output_siggen_power = self.findChild(
            QtWidgets.QLCDNumber, "output_siggen_power")

        # Timer
        self.timer = QtCore.QTimer(self)
        self.timer.start(100)
        self.timer.timeout.connect(self.update_display)

        self.show()  # Show the GUI

    def enable_rf(self):
        if self.input_rf_enabled.isChecked():
            return 1
        else:
            return 0

    def update_display(self):
        self.output_siggen_freq.display(meas_freq)
        self.output_siggen_power.display(meas_power)

if __name__ == '__main__':

    meas_freq = 0
    meas_power = 0

    sig_gen = SignalGenerator()
    sig_gen.connect()

    gui = QtWidgets.QApplication(sys.argv)
    window = Ui()
    gui.exec_()