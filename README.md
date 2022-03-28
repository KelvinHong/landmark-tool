# LandmarkTool for Machine Learning Labeling

## Introduction

Need to annotate a huge dataset by landmarks? This is a perfect tool for you.
This simple GUI tool let you import images from your folder, then annotate them with a predefined number of landmarks. 

It supports Redo functionality, which means if you accidentally mislabeled a landmark, simply press Redo, then it will clear all landmarks on current image then let you annotate again.

It also supports resume functionality, which means if you want to take a break, just press the "take a break" button. 
That will exit the program safely.
To resume your work, simply open the program then it will redirect you to your current image.
This is because we have saved your inputs so you do not need to enter these information again.

## Prerequisite

After cloning the repository, run 
```
pip install -r requirements.txt
```
Then the program should be working fine.

This program is developed on Windows 10, Python 3.9.

## How to use it

Use our sample folder `polo_images/` for illustration. 
Run
```
python app.py
```
An interface will pop up. 
Follow the instruction, choose the `polo_images/` folder and enter `10` landmarks, then you can start annotate the images. 
You can enter your choice of number of landmarks, `10` is being served as an example.

We will save your landmarks coordinate into `annotation/polo_images.csv`, which is a csv file. 
The csv file name is taken from your folder name.
You will see the columns as `x1,y1,x2,y2,...`. 
The `x,y` coordinates are recorded with top-left origin, which means the top-left corner of the image is recorded as `0,0`. 