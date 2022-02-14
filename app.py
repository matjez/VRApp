import cv2
import time
import os
import numpy as np
import json

from datetime import datetime
from pathlib import Path

class Camera:

    def __init__(self, name, camera_num=0,folder_path="recordings") -> None:
        self.settings = self.get_settings("name")

        self.folder_path = folder_path
        self.camera_num = camera_num

        self.max_weight = 8192

        self.vid_capture = cv2.VideoCapture(camera_num)
        self.vid_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings["resolution_x"])
        self.vid_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings["resolution_y"])
        self.vid_capture.set(cv2.CAP_PROP_FPS, self.settings["fps"])

    def test_device(self, camera_num):
        """Check if camera is available"""
        if self.vid_capture is None or not self.vid_capture.isOpened():
            print('Warning: unable to open video source: ', camera_num)
            exit()

    def create_path(self):
        """Create path for new clip"""       
        cur_date = datetime.now().strftime(self.settings["rec_pattern"])
        path = "{}{}.{}".format(self.settings["rec_folder"],
            cur_date, self.settings["extension"])

        return path

    def check_weight(self,path):
        """Checks weight and returns value in MB"""
        weight_kb = Path(path).stat().st_size
        weight_mb = round(weight_kb / (1024 * 1024), 3)
        
        return weight_mb

    def capture_video(self):

        path = self.create_path()
        print(path)

        path = "video_clip.avi"

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.output = cv2.VideoWriter(path, fourcc, self.settings["fps"], (self.settings["resolution_x"],
         self.settings["resolution_y"]))

        start_time = time.time()
        frame_count = 0
        duration = 0
        while True:
            ret, frame = self.vid_capture.read()
            if not ret:
                print('empty frame')
                break
            self.output.write(frame)  # write each frame to make video clip
            frame_count += 1

            duration = time.time()-start_time
            if int(duration) == self.settings["rec_length"]:

                actualFps = np.ceil(frame_count/duration) 
                duration = 0
                frame_count = 0
                
                self.output.release()
                self.vid_capture.release()

                os.system('ffmpeg -y -i {} -c copy -f h264 tmp.h264'.format(path))
                os.system('ffmpeg -y -loglevel error -r {} -i tmp.h264 -c copy {}'.format(actualFps,path))

                if os.path.exists("tmp.h264"):
                    os.remove("tmp.h264")

        self.vid_capture.release()
        self.output.release()
        cv2.destroyAllWindows()

    def _set_def_settings(self, config_file, name):
        """Sets default settings"""
        new_settings = {name:{}}

        new_settings[name]["resolution_x"] = 1280
        new_settings[name]["resolution_y"] = 720
        new_settings[name]["fps"] = 30.0
        new_settings[name]["extension"] = "avi"
        new_settings[name]["rec_folder"] = "recordings/{}/".format("name") # add name of camera
        new_settings[name]["rec_pattern"] = r"%Y-%m-%d %H-%M-%S"
        new_settings[name]["rec_length"] = 180

        config_file.update(new_settings)
        config_file = json.dumps(config_file, indent=4)

        with open("config.json","w") as f:
            f.write(config_file)
        
        return new_settings

        
    def get_settings(self, name):
        """Returns settings from config.json. If there is no any settings in file
        sets default settings and save it to config.json
        """
        with open("config.json","r") as f:
            config_file = f.read()
            config_file = json.loads(config_file)

        if name in config_file.keys():
            return config_file[name]

        else:
            return self._set_def_settings(config_file,name)


if __name__ == "__main__":
    my_camera = Camera("name")
    my_camera.capture_video()

    print(my_camera.get_settings("kamera_1"))
