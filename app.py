import cv2
import time
import os
import numpy as np
import json
import platform

from matplotlib import pyplot as plt
from datetime import datetime
from pathlib import Path
from threading import Thread


class Camera:

    camera_nums = []
    all_settings = set()

    def __init__(self) -> None:
        self.max_weight = 8192

        self.preview_camera = None
        self.stop_flag = False

    def start(self, timer, rec_type, speed, ip_cameras = []):
        """Start threads. Searching for available devices and creating thread for every detected camera."""
        if rec_type == "ip":
            for camera in ip_cameras:
                Camera.camera_nums.append(camera)
                self.set_preview(camera)
                settings = Camera.get_settings(str(camera))     
                loop_thread = Thread(target=self.capture_video,args=(i, settings, timer, speed,))
                
        else:
            for i in range(1):  # 0 - 9
                if self.check_if_available(i) == False:
                    break
                
                Camera.camera_nums.append(i)
                settings = Camera.get_settings(str(i))
                self.set_preview(i)

                if rec_type == "default":
                    loop_thread = Thread(target=self.capture_video,args=(i, settings, timer, speed,))
                elif rec_type == "motion":
                    loop_thread = Thread(target=self.capture_motion,args=(i, settings, timer,)) 
                else:
                    break

                loop_thread.daemon = True
                loop_thread.start()

    def restart(self):
        """Stops every thread. If all threads are handled creates new ones."""
        self.terminate_threads()
        self.start()

    def set_preview(self, name):
        self.preview_camera = name

    def terminate_threads(self):
        """Set flag 'stop_flag' to True which will cause terminating of all threads."""
        self.stop_flag = True
        Camera.camera_nums = []

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

    def save_video(self, path, actualFps):
        """Copy recorded file to tmp.h264 then convert to corrected fps."""
        os.system('ffmpeg -y -i "{}" -c copy -f h264 tmp.h264'.format(path))
        os.system('ffmpeg -y -loglevel error -r {} -i tmp.h264 -c copy "{}"'.format(actualFps,path))

        if os.path.exists("tmp.h264"):
            os.remove("tmp.h264")

    def capture_video(self, camera_num, settings, timer=None, speed=1):
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
                    duration = time.time()-start_time
                    actualFps = np.ceil(frame_count/duration)
                    self.output.release()
                    self.save_video(path, actualFps)
                    break

            ret, frame = self.vid_capture.read()

            if self.stop_flag == True or not ret:
                print("Exiting")
                break

            if self.preview_camera == camera_num:
                cv2.imshow('Preview', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
            self.output.write(frame)  # write each frame to make video clip
            duration = time.time()-start_time

            frame_count += 1
            # print(duration)
            if int(duration) >= settings["rec_length"]:
                if speed != None:
                    frame_count = frame_count / speed

                actualFps = np.ceil(frame_count/duration) 
                start_time = time.time()
                frame_count = 0

                self.output.release()
                self.save_video(path, actualFps)

                path = self.create_path(settings, camera_num)
                self.output = cv2.VideoWriter(path, fourcc, settings["fps"], (settings["resolution_x"],
                    settings["resolution_y"]))

        self.vid_capture.release()
        self.output.release()
        cv2.destroyAllWindows()

    def capture_motion(self, camera_num, settings, timer):
        """Recording video with motion detection."""
        self.vid_capture = cv2.VideoCapture(camera_num)
        self.vid_capture.set(cv2.CAP_PROP_FRAME_WIDTH, settings["resolution_x"])
        self.vid_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, settings["resolution_y"])
        self.vid_capture.set(cv2.CAP_PROP_FPS, settings["fps"])
 
        ret, frame1 = self.vid_capture.read()
        ret, frame2 = self.vid_capture.read()

        path = self.create_path(settings, camera_num)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.output = cv2.VideoWriter(path, fourcc, settings["fps"], (settings["resolution_x"],
            settings["resolution_y"]))

        timer = settings["motion_length"]
        movement_time = time.time() # time when last movement intercepted
        start_time = time.time() # time when started recording current clip

        out_released = False
        frame_count = 0
        duration = 0

        while self.vid_capture.isOpened():
            if timer != None:
                if time.time() - start_time >= timer:
                    duration = time.time()-start_time
                    actualFps = np.ceil(frame_count/duration)
                    self.save_video(path, actualFps)
                    break

            diff = cv2.absdiff(frame1, frame2)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            contours, _ = cv2.findContours(
                dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                (x, y, w, h) = cv2.boundingRect(contour)
                if cv2.contourArea(contour) < 3000:
                    continue
                cv2.rectangle(frame1, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame1, "Status: {}".format('Movement'), (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 0, 0), 3)

                movement_time = time.time()

                if out_released == True:
                    out_released = False
                    path = self.create_path(settings, camera_num)
                    self.output = cv2.VideoWriter(path, fourcc, settings["fps"], (settings["resolution_x"],
                        settings["resolution_y"]))

            # cv2.drawContours(frame1, contours, -1, (0, 255, 0), 2)
            # cv2.imshow("Video", frame1)

            frame1 = frame2
            ret, frame2 = self.vid_capture.read()
            frame_count += 1

            if time.time() - movement_time <= timer:  # if last detected movement < timer write video
                print(time.time() - movement_time)
                if out_released == False:
                    self.output.write(frame1)

            elif out_released == False:              # if interval between clips occured start new video writer
                print("else")
                duration = time.time()-start_time
                actualFps = np.ceil(frame_count/duration) 
                
                # reset variables
                start_time = time.time()
                frame_count = 0
                out_released = True
                
                self.output.release()
                self.save_video(path, actualFps)    # need to make threading
                

            else:
                print("pass")
                pass

            # if cv2.waitKey(50) == 27:
            #     break

        self.vid_capture.release()
        cv2.destroyAllWindows()
    
    @staticmethod
    def _set_def_settings(config_file, name):
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
        new_settings[name]["motion_length"] = 30

        config_file.update(new_settings)
        config_file = json.dumps(config_file, indent=4)

        with open("config.json","w") as f:
            f.write(config_file)
        
        return new_settings

    @classmethod
    def get_settings(cls,name):
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
            settings = Camera._set_def_settings(config_file,name)
            cls.all_settings.add(settings)
            return settings

    @staticmethod
    def check_weight(path):
        """Checks weight and returns value in MB"""
        weight_kb = Path(path).stat().st_size
        weight_mb = round(weight_kb / (1024 * 1024), 3)
        
        return weight_mb

if __name__ == '__main__':
    my_camera = Camera()
    my_camera.capture_video(0, my_camera.get_settings(0), None, 1)
    # my_camera.capture_motion(0, Camera.get_settings(0), 1)
    print("test")
    time.sleep(3)
    my_camera.set_preview(0)


    time.sleep(100)
