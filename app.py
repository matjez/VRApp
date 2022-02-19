import cv2
import time
import os
import numpy as np
import json
import platform

from datetime import datetime
from pathlib import Path
from threading import Thread


class Camera:

    camera_nums = []

    def __init__(self) -> None:

        self.max_weight = 8192
        self.stop_flag = False

    def start(self, timer, rec_type, speed):
        """Start threads. Searching for available devices and creating thread for every detected camera."""
        for i in range(1):  # 0 - 9
            if self.check_if_available(i) == False:
                break
            
            Camera.camera_nums.append(i)
            settings = self.get_settings(str(i))
            loop_thread = Thread(target=self.capture_video,args=(i, settings, timer, rec_type, speed,)) #(x,)
            loop_thread.daemon = True
            loop_thread.start()

    def restart(self):
        """Stops every thread. If all threads are handled creates new ones."""
        self.terminate_threads()
        self.start()

    def terminate_threads(self):
        """Set flag 'stop_flag' to True which will cause terminating of all threads."""
        self.stop_flag = True

    def test_device(self, camera_num):
        """Check if camera is available"""
        if self.vid_capture is None or not self.vid_capture.isOpened():
            print('Warning: unable to open video source: ', camera_num)
            exit()

    def create_path(self, settings, camera_num):
        """Create path for new clip. Works for Windows and Linux"""    
        cur_date = datetime.now().strftime(settings["rec_pattern"])

        if platform.system() == "Linux":
            path = "{}/{}/{}.{}".format(settings["rec_folder"], camera_num,
                cur_date, settings["extension"])

        elif platform.system() == "Windows":
            path = "{}\\{}\\{}.{}".format(settings["rec_folder"], camera_num,
                cur_date, settings["extension"])

        return path

    def check_weight(self,path):
        """Checks weight and returns value in MB"""
        weight_kb = Path(path).stat().st_size
        weight_mb = round(weight_kb / (1024 * 1024), 3)
        
        return weight_mb

    def check_if_available(self, camera_num):
        """Check if camera is up and return True or False"""
        self.vid_capture = cv2.VideoCapture(camera_num)
        if self.vid_capture.read()[0]==False:
            self.vid_capture.release()
            print(False)
            return False 
            
        else:
            self.vid_capture.release()
            print(True)
            return True

    def save_video(self, path, actualFps, speed=None):
        """Copy recorded file to tmp.h264 then convert to corrected fps."""
        os.system('ffmpeg -y -i "{}" -c copy -f h264 tmp.h264'.format(path))
        os.system('ffmpeg -y -loglevel error -r {} -i tmp.h264 -c copy "{}"'.format(actualFps,path))

        if os.path.exists("tmp.h264"):
            os.remove("tmp.h264")


    def capture_video(self, camera_num, settings, timer=None, rec_type="loop", speed=1):
        """Create VideoCapture object and record videos"""
        self.vid_capture = cv2.VideoCapture(camera_num)
        self.vid_capture.set(cv2.CAP_PROP_FRAME_WIDTH, settings["resolution_x"])
        self.vid_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, settings["resolution_y"])
        self.vid_capture.set(cv2.CAP_PROP_FPS, settings["fps"])
        
        path = self.create_path(settings, camera_num)

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.output = cv2.VideoWriter(path, fourcc, settings["fps"], (settings["resolution_x"],
         settings["resolution_y"]))

        start_time = time.time()
        frame_count = 0
        duration = 0
        
        while True:

            if timer != None:
                if time.time() - start_time >= timer:
                    actualFps = np.ceil(frame_count/duration)
                    self.save_video(path, actualFps)
                    break

            ret, frame = self.vid_capture.read()

            if self.stop_flag == True or not ret:
                break

            self.output.write(frame)  # write each frame to make video clip
            duration = time.time()-start_time

            frame_count += 1

            if int(duration) == 10:

                if speed != None:
                    frame_count = frame_count / speed

                actualFps = np.ceil(frame_count/duration) 
                duration = 0
                frame_count = 0

                self.output.release()
                self.save_video(path, actualFps)

                self.output = cv2.VideoWriter(path, fourcc, settings["fps"], (settings["resolution_x"],
                    settings["resolution_y"]))

        self.vid_capture.release()
        self.output.release()
        cv2.destroyAllWindows()

    def _set_def_settings(self, config_file, name):
        """Sets default settings for specified camera."""
        new_settings = {name:{}}

        new_settings[name]["resolution_x"] = 1280
        new_settings[name]["resolution_y"] = 720
        new_settings[name]["fps"] = 30.0
        new_settings[name]["extension"] = "avi"
        new_settings[name]["rec_folder"] = "recordings" # add name of camera
        new_settings[name]["rec_pattern"] = r"%Y-%m-%d %H-%M-%S"
        new_settings[name]["rec_length"] = 180
        new_settings[name]["timer_length"] = 300

        config_file.update(new_settings)
        config_file = json.dumps(config_file, indent=4)

        with open("config.json","w") as f:
            f.write(config_file)
        
        return new_settings

    def get_settings(self, name):
        """Returns settings from config.json. If there is no any settings in file
        sets default settings and save it to config.json
        """
        name = str(name)

        with open("config.json","r") as f:
            config_file = f.read()
            config_file = json.loads(config_file)

        if name in config_file.keys():
            return config_file[name]

        else:
            return self._set_def_settings(config_file,name)

if __name__ == '__main__':
    my_camera = Camera()
    my_camera.capture_video(0, my_camera.get_settings(0), None, "loop", 1)

    time.sleep(100)
