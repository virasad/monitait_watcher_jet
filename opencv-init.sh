sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install build-essential cmake unzip pkg-config gfortran -y
sudo apt-get install libjpeg-dev libpng-dev libtiff-dev -y
sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev -y
sudo apt-get install libxvidcore-dev libx264-dev -y
sudo apt-get install libhdf5-dev libhdf5-serial-dev -y
sudo apt-get install libgtk-3-dev -y
sudo apt-get install libatlas-base-dev libblas-dev liblapack-dev -y
sudo apt-get install python3-dev -y
sudo apt-get install libopenblas-dev -y
sudo python3 -m pip install --upgrade pip setuptools wheel
sudo pip3 install -U numpy==1.26.4
sudo pip3 install opencv-python==3.4.18.65

