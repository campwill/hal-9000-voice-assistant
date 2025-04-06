import drivers.apa102 as apa102
import time
import threading
import queue

# Referenced https://github.com/respeaker/mic_hat/blob/master/interfaces/pixels.py

class Lights:
    NUM_LIGHTS = 3

    def __init__(self):
        self.dev = apa102.APA102(num_led=self.NUM_LIGHTS)

        self.next = threading.Event()
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def off(self):
        self.next.set()
        self.queue.put(self._off)

    def fade_in(self):
        self.next.set()
        self.queue.put(self._fade_in)

    def fade_out(self):
        self.next.set()
        self.queue.put(self._fade_out)

    def _run(self):
        while True:
            func = self.queue.get()
            func()

    def _fade_in(self):
        for i in range(256):
            red_intensity = i
            colors = [red_intensity, 0, 0] * self.NUM_LIGHTS
            self.write(colors)
            time.sleep(0.01)

    def _fade_out(self):
        for i in range(255, -1, -1):
            red_intensity = i
            colors = [red_intensity, 0, 0] * self.NUM_LIGHTS
            self.write(colors)
            time.sleep(0.01)

    def _off(self):
        self.write([0] * 3 * self.NUM_LIGHTS)

    def write(self, colors):
        for i in range(self.NUM_LIGHTS):
            self.dev.set_pixel(i, int(colors[3*i]), int(colors[3*i + 1]), int(colors[3*i + 2]))

        self.dev.show()
