from app import Camera
import time

class Controller():
    def __init__(self) -> None:
    
        self.camera_obj = Camera()
        
    #timer=100 type="loop"

    def loop_recording(self, timer=None):
        self.camera_obj.start(rec_type="loop", timer=timer, speed=1)

    def motion_recording(self, timer=None):
        self.camera_obj.start(rec_type="motion", timer=timer, speed=1)

    def time_lapse(self, timer=None):
        self.camera_obj.start(rec_type="time_lapse", timer=timer, speed=8)

    def terminate_recording(self, timer=None):
        self.camera_obj.terminate_threads()

    def restart_thread(self, timer=None):
        self.camera_obj.restart()

test = Controller()
test.loop_recording()
time.sleep(100)