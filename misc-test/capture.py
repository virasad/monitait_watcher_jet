from time import sleep
from picamera import PiCamera

camera = PiCamera()
camera.resolution = (2592, 1544)
#camera.start_preview()
# Camera warm-up time
sleep(1)
while True:
    sleep(2)
    camera.capture('image.jpg', use_video_port=True)
    sleep(2)
