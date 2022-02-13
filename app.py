
from webbrowser import get
import cv2
import time
import os
import numpy as np
import json

from datetime import datetime
from pathlib import Path
from tools import get_camera_settings

class Camera:

    def __init__(self, name, camera_num=0,folder_path="recordings") -> None:

        if name in get_camera_settings():
            self.settings = get_camera_settings()

        else:
            self.settings = self.set_def_settings()

        self.folder_path = folder_path
        self.camera_num = camera_num

        self.extension = "avi"
        self.max_weight = 8192

        self.vid_capture = cv2.VideoCapture(camera_num)
        self.vid_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.vid_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.vid_capture.set(cv2.CAP_PROP_FPS, 30.0)

    def test_device(self, camera_num):
        """Check if camera is available"""

        if self.vid_capture is None or not self.vid_capture.isOpened():
            print('Warning: unable to open video source: ', camera_num)
            exit()

    def create_path(self):
        """Create path for new clip"""       

        cur_date = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        path = "{}/{}/{}.{}".format(self.folder_path, self.camera_num,
            cur_date, self.extension)

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
        self.output = cv2.VideoWriter(path, fourcc, 30.0, (1280, 720))
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
            if int(duration) == 180:
                duration = 0
                self.output.release()
                self.vid_capture.release()
                # break

            actualFps = np.ceil(frame_count/duration) 

        os.system('ffmpeg -y -i {} -c copy -f h264 tmp.h264'.format(path))
        os.system('ffmpeg -y -r {} -i tmp.h264 -c copy {}'.format(actualFps,path))

        self.vid_capture.release()
        self.output.release()
        cv2.destroyAllWindows()

    @staticmethod
    def set_def_settings():
        new_settings = {}

        new_settings["resolution_x"] = 1280
        new_settings["resolution_y"] = 720
        new_settings["fps"] = 30.0
        new_settings["extension"] = "avi"
        new_settings["rec_folder"] = "recordings/{}".format("name") # add name of camera
        new_settings["rec_pattern"] = r"%Y-%m-%d %H-%M-%S"
        new_settings["rec_length"] = 180

        json_object = json.dumps(new_settings, indent=4)

        with open("config.json","w") as f:
            f.write(json_object)
        
        return new_settings


if __name__ == "__main__":
    my_camera = Camera("name")
    my_camera.capture_video()

    print(my_camera.set_def_settings())
