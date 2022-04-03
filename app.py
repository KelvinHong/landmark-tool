from typing import List, Literal, Tuple
import PySimpleGUI as sg
import os
import json
import time
import pandas as pd
from PIL import Image, ImageTk
import io
from io import BytesIO
import textwrap
import state
from utils import pretty_dump, inspect_annotation_json

CACHE = "cachefile.json"
ANNOTATION = "annotation/"

def front_page():
    sg.theme('BrightColors')   # Add a touch of color
    # All the stuff inside your window.
    homepage = [[sg.Text('Welcome to LandmarkTool!',  size=(40, 1), font=('Any 15'))],
                [sg.Text('This application let you label images for machine learning purpose.')],
                [sg.Text('(Press Enter key or Spacebar to navigate quickly)')],
                [sg.Button('Start', bind_return_key=True, button_color=("black", "green")),
                sg.Button('Cancel', button_color=("black", "grey"))]]
    # Create the Window
    window = sg.Window('Home Page', homepage)
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
            break
        elif event == 'Start':
            window.close()
            input_info()

    window.close()

def input_info():
    sg.theme('GrayGrayGray')
    # Set default value
    dataset_default = "" 
    numlm_default = ""
    dynamic_lm = False
    # Detect cache file
    cache_flag = os.path.isfile(CACHE)
    if cache_flag and os.stat(CACHE).st_size != 0: 
        with open(CACHE, "r") as f:
            store = json.load(f)
        dataset_default = store["-FOLDER-"]
        dynamic_lm = store["-DYNAMIC-"]
        if not dynamic_lm:
            numlm_default = store["-NUMLM-"]
    else:
        cache_flag = False
        store = {}
    input_info = [
                [sg.Text('Information Input here:',  size=(40, 1), font=('Any 15'))],
                [sg.Text("Previous data restored! You're welcome.", visible=cache_flag)],
                [sg.Text('Images Dataset'), sg.Input(size=(60,1), enable_events=True ,key='-FOLDER-', default_text=dataset_default), sg.FolderBrowse()],
                [sg.Text('Number of landmarks'), sg.Input(size=(5,1), key='-NUMLM-', default_text=numlm_default, disabled=dynamic_lm), sg.Checkbox("Dynamic Landmarks", key = '-DYNAMIC-', default=dynamic_lm, enable_events=True)],
                [
                    sg.Button('Continue', bind_return_key=True, button_color=("black", "lightblue"), focus=True, enable_events=True), 
                    sg.Button('Back', button_color=("black", "grey")), 
                    sg.Button('Cancel', button_color=("black", "grey"))
                ]
            ]
    window = sg.Window('Information Page', input_info, finalize=True)
    while True:
        event, values = window.read()
        if event in [sg.WIN_CLOSED, "Cancel"]:
            return 
        elif event == "-DYNAMIC-":
            if values["-DYNAMIC-"]: window["-NUMLM-"].Update(disabled = True)
            else: window["-NUMLM-"].Update(disabled = False)
        elif event == "Continue":
            dataset_Dir = values["-FOLDER-"]
            dynamic_lm = values["-DYNAMIC-"]
            if not dynamic_lm:
                num_lm = values["-NUMLM-"]
            # validate 
            if dataset_Dir == "" or not os.path.isdir(dataset_Dir):
                message = f"Please choose a valid folder."
                sg.popup(message)
                continue
            if not os.access(dataset_Dir, os.R_OK):
                message = f"You do not have access to the dataset folder:\n{dataset_Dir}\nPlease try again."
                sg.popup(message)
                continue
            if not dynamic_lm:
                if num_lm == "":
                    message = f"Number of landmark shouldn't be empty"
                    sg.popup(message)
                    continue
                elif not num_lm.isdigit():
                    message = f"Number of landmark should be a valid positive number"
                    sg.popup(message)
                    continue
            # If all validations passed, store the variables in a file.
            
            store.update({
                "-FOLDER-": dataset_Dir, 
                "-DYNAMIC-": dynamic_lm
            })
            if not dynamic_lm:
                store["-NUMLM-"] = int(num_lm)
            elif "-NUMLM-" in store:
                del store["-NUMLM-"]
            pretty_dump(store, CACHE)
            break
            # popup("Your input has been processed. ", "info")
        elif event == "Back":
            window.close()
            front_page()
            return 
    window.close()
    annotate()


def annotate():
    sg.theme('Dark')
    with open(CACHE, "r") as f:
        data = json.load(f)
        Dir = data["-FOLDER-"]
        dynamic_lm = data["-DYNAMIC-"]
        if not dynamic_lm:
            total_num_lm = int(data["-NUMLM-"])
        else:
            total_num_lm = None
    w, h = sg.Window.get_screen_size()
    image_gap = int(0.72*h)
    column_width = int(0.25*w)
    image_filetypes =  [("All files (*.*)", "*.*"),
                        ("JPG (*.jpg)", "*.jpg"),
                        ("JPEG (*.jpeg)", "*.jpeg"),
                        ("PNG (*.png)", "*.png"),
                        ]
    # Landmark Progress bar behavior depends on dynamic landmark setting
    if not dynamic_lm:
        landmark_element = [
                        sg.Text(f"Landmark Progress: i/n", key="-LMPROGRESS-"),
                        sg.ProgressBar(max_value=10, orientation="horizontal", bar_color=("green", "white"), size=(30, 10), key="-LBAR-"),
                    ]
    else:
        landmark_element = [sg.Text(f"Landmark Progress: i", key="-LMPROGRESS-")]
    left_col = sg.Col([
                    [sg.Text("You are labeling [image_name]", font=('Any 15'), key="-IMAGETEXT-")],
                    [sg.Text(f"from folder {Dir} .")],
                    [
                        sg.Text(f"Annotation Progress: i/n", key="-ANNOPROGRESS-"),
                        sg.ProgressBar(max_value=10, orientation="horizontal", bar_color=("green", "white"), size=(30, 10), key="-PBAR-"),
                    ],
                    landmark_element,
                    [
                        sg.Col([
                            [sg.Table(values=[], key="-LMTABLE-", headings=["Id", "x", "y"], col_widths=column_width, max_col_width=column_width, auto_size_columns=False, justification="center", expand_y=True)],
                            [sg.Text("", visible = False, key="-TABLEPROMPT-")]
                        ], expand_y = True),
                        sg.Col([
                                [sg.Text("Template Image", font=('Any 15'))],
                                [sg.Text("Load reference image here")],
                                [sg.Image(filename="./media/white.png", size=(column_width, int(h/2)), key="-TEMPLATE-IMG-")],
                                [sg.Input(key="-TEMPLATE-FILE-", size=(20,1)), sg.FileBrowse(file_types=image_filetypes), sg.Button("Load Template")]
                            ])
                    ]
                ], size=(int(w/2), h), pad=(0,0))
    right_col = sg.Col([
                    [
                        sg.Button("Undo (Ctrl+Z)", key="-UNDO-", enable_events= True),
                        sg.Button("Redo Image", key='-REDO-'),
                        sg.Push(),
                        sg.Text("W = 0px, H = 0px", key="-IMAGE-INFO-", visible=False),
                    ],
                    [
                        sg.Button("<", key="-PREV-"),
                        sg.Graph(
                            canvas_size=(image_gap, image_gap),
                            graph_bottom_left=(0, 0),
                            graph_top_right=(image_gap, image_gap),
                            key="-GRAPH-",
                            change_submits=True,  # mouse click events
                            background_color='white'
                        ),
                        sg.Button(">", key='-NEXT-', bind_return_key=True),
                    ],
                    [
                        sg.Button('Save', button_color=("black", "lightyellow")),
                        sg.Push(),
                        sg.Text("", visible=False, key = "-HOVER-OUTPUT-")
                    ],
                ], size=(int(w/2), h), pad=(0,0))
    left_frame = sg.Frame("Input data",  [[left_col]])
    right_frame = sg.Frame("Image", [[right_col]])
    label_window = [[left_frame, right_frame]]
    window = sg.Window('Annotation Window', label_window, resizable=True, finalize=True)
    window.Maximize()
    # Create annotation json file or use existing ones. 
    annotation_json, new_file = inspect_annotation_json(Dir, total_num_lm)
    # Get all image paths
    image_exts = [".jpg", ".png", ".jpeg"]
    all_image_paths = [os.path.basename(p) for p in os.listdir(Dir) if os.path.splitext(p)[1].lower() in image_exts]
    total_image_num = len(all_image_paths)
    # Check which image haven't been annotated
    ## Use pointer, user currently looking at this image
    pointer = 0
    with open(CACHE, "r") as f:
        data = json.load(f)
    if "pointer" not in data:
        data["pointer"] = 0
        pretty_dump(data, CACHE)
    else:
        pointer = data["pointer"]
    # Collect info for Window State Machine
    info = {"total_num_lm": total_num_lm,
            "total_num_images": total_image_num,
            "dir": Dir, 
            "annotation_json": annotation_json,
            "all_image_rel_paths": all_image_paths, 
            "pointer": pointer, 
            "image_gap": image_gap,
            "column_width": column_width,
            "dynamic_lm": dynamic_lm
        }
    # Load template image if exist
    if os.path.isfile(CACHE):
        with open(CACHE, "r") as f:
            data = json.load(f)
        # Template file exists
        if "-TEMPLATE-FILE-" in data:
            info["template_file"] = data["-TEMPLATE-FILE-"]
    # State Machine created
    WSM = state.WindowStateMachine(window, data = info)
    WSM.window_init()

    # Bind Motion (hover) for graph
    window["-GRAPH-"].bind("<Motion>", "Moved")
    # Bind Ctrl+Z for Undo landmark
    window.bind('<Control-z>', 'UNDO')
    # Event detection
    while True:
        event, values = window.read()
        # Disable prompt text after one event
        if window["-TABLEPROMPT-"].visible and event != '-GRAPH-Moved':
            window["-TABLEPROMPT-"].Update(visible=False)
        if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
            break
        elif event == '-GRAPH-Moved':
            mouse = values['-GRAPH-']
            x, y = WSM.mouse_to_xy(mouse)
            window["-HOVER-OUTPUT-"].Update(f"Location [{x},{y}]", visible=True)
        elif event == '-GRAPH-':
            mouse = values['-GRAPH-']
            # If it is not mouse click
            if mouse == (None, None):
                continue
            # State Machine Plot the point, increase num_lm and save to table database. 
            WSM.plot_point(mouse)
        elif event == '-NEXT-':
            # next_button = window["-NEXT-"]
            # Validate landmark counter
            # Number of landmark detected wrong.
            message = WSM.next_image()
            if message == "Home":
                window.close()
                front_page()
                # Remove state machine
                del WSM
        elif event == '-PREV-':
            WSM.prev_image()
        elif event in ["-UNDO-", "UNDO"]:
            WSM.undo_landmark()
        elif event == "-REDO-":
            WSM.renew_annotate(request = "redo")
            WSM.table_prompt("REDO: Table has been cleared.")
        elif event == "Load Template":
            filename = values["-TEMPLATE-FILE-"]
            if filename == "":
                sg.popup("Please 'Browse' for template image before loading it.")
                continue
            elif not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
                sg.popup("Please make sure the template image is typed correctly.\n" \
                    + "If you use browsing, shouldn't have this problem\n" \
                    + "Kindly also ensure you have permission to read the image.")
                continue
            # Store the filename only if it is valid
            WSM.template_file = filename
            WSM.load_template()
            # Update cache file
            with open(CACHE, "r") as f:
                data = json.load(f)
            data["-TEMPLATE-FILE-"] = filename
            pretty_dump(data, CACHE)
        elif event == 'Save':
            response = WSM.save_session()
            if response == "Yes":
                window.close()
                front_page()
    window.close()
        

if __name__ == "__main__":
    # sg.theme_previewer()
    front_page()