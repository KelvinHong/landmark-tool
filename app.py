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

CACHE = "cachefile.json"
ANNOTATION = "annotation/"

def popup(message: str, style: Literal["warning", "info"] = "warning"):
    if style == "warning":
        sg.theme('DarkRed2')
        window_name = 'Something\'s Wrong'
        button_color = ("black", "yellow")
    elif style == "info":
        sg.theme('DarkTeal7')
        window_name = 'Info'
        button_color = ("black", "lightblue")
    mes = [[sg.Text(message)],
            [sg.Button('I Got It', size=(40,1), button_color=button_color, bind_return_key=True)]]
    # Create the Window
    window = sg.Window(window_name, mes)
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
            break
        elif event == 'I Got It':
            window.close()

    window.close()

def alert(message: str, responses: Tuple[str, str] = ["OK", "Nope"]) -> bool:
    sg.theme('DarkTeal7')
    window_name = '--Attention--'
    button_color = ("black", "lightblue")
    agree = responses[0]
    disagree = responses[1]
    mes = [[sg.Text(message)],
            [sg.Button(agree, button_color=("black", "green"), bind_return_key=True), 
            sg.Button(disagree, button_color=("black", "grey"))]]
    # Create the Window
    window = sg.Window(window_name, mes)
    # Logic
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
            popup("Exited the program safely.")
            exit()
        elif event == agree:
            window.close()
            return True
        elif event == disagree:
            window.close()
            return False

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
    # Detect cache file
    dataset_default = "" 
    numlm_default = ""
    cache_flag = os.path.isfile(CACHE)
    if cache_flag: 
        with open(CACHE, "r") as f:
            store = json.load(f)
        dataset_default = store["-FOLDER-"]
        numlm_default = store["-NUMLM-"]
    else:
        store = {}
    input_info = [
                [sg.Text('Information Input here:',  size=(40, 1), font=('Any 15'))],
                [sg.Text("Previous data restored! You're welcome.", visible=cache_flag)],
                [sg.Text('Dataset'), sg.Input(size=(60,1), enable_events=True ,key='-FOLDER-', default_text=dataset_default), sg.FolderBrowse()],
                [sg.Text('Number of landmarks'), sg.Input(size=(5,1), key='-NUMLM-', default_text=numlm_default)],
                [sg.Text("Your input has been processed. ", key="info", visible=False)],
                [
                    sg.Button('Continue', bind_return_key=True, button_color=("black", "lightblue"), focus=True, enable_events=True), 
                    sg.Button('Back', button_color=("black", "grey")), 
                    sg.Button('Cancel', button_color=("black", "grey"))
                ]
            ]
    window = sg.Window('Information Page', input_info, finalize=True)
    validated = False
    while True:
        event, values = window.read()
        if event in [sg.WIN_CLOSED, "Cancel"]:
            break
        elif event == "Continue":
            dataset_dir = values["-FOLDER-"]
            num_lm = values["-NUMLM-"]
            # validate 
            if dataset_dir == "" or not os.path.isdir(dataset_dir):
                message = f"Please choose a valid folder."
                popup(message)
                continue
            if not os.access(dataset_dir, os.R_OK):
                message = f"You do not have access to the dataset folder:\n{dataset_dir}\nPlease try again."
                popup(message)
                continue
            if num_lm == "":
                message = f"Number of landmark shouldn't be empty"
                popup(message)
                continue
            elif not num_lm.isdigit():
                message = f"Number of landmark should be a valid positive number"
                popup(message)
                continue
            # If all validations passed, store the variables in a file.
            with open(CACHE, "w") as f:
                store.update({"-FOLDER-": dataset_dir, "-NUMLM-": num_lm})
                json.dump(store, f)
            time.sleep(0.1)
            window['info'].Update(visible=True)
            validated = True
            break
            # popup("Your input has been processed. ", "info")
        elif event == "Back":
            window.close()
            front_page()
    window.close()
    if validated: annotate(dataset_dir, int(num_lm))

def load_image(window, dir: str, img_name: str, image_gap: int):
    im = Image.open(os.path.join(dir, img_name))
    w, h = im.size
    im = im.resize((image_gap, image_gap), resample = Image.BICUBIC)
    tmp1 = "./tmp/cache_img1.png"
    im.save(tmp1)
    with BytesIO() as output:
        im.save(output, format="PNG")
        data = output.getvalue()
    window["-GRAPH-"].DrawImage(data = data, location= (0, image_gap))
    return w, h

def renew_annotate(window, dir, img_path, image_gap, annotated_num, total_image_num, num_lm):
    ori_w, ori_h = load_image(window, dir, img_path, image_gap)
    window["-IMAGETEXT-"].Update(f"You are labeling {img_path}")
    window["-ANNOPROGRESS-"].update(f"Annotation Progress: {annotated_num}/{total_image_num}")
    window["-LMPROGRESS-"].update(f"Landmark Progress: 0/{num_lm}")
    window["-LMTABLE-"].update(values = [])
    window["-PBAR-"].update(current_count = annotated_num, max = total_image_num)
    window["-LBAR-"].update(current_count = 0, max = num_lm)

def annotate(dir: str, num_lm: int):
    sg.theme('Dark')
    w, h = sg.Window.get_screen_size()
    image_gap = int(0.75*h)
    column_width = int(0.25*w)
    image_filetypes =  [("All files (*.*)", "*.*"),
                        ("JPG (*.jpg)", "*.jpg"),
                        ("JPEG (*.jpeg)", "*.jpeg"),
                        ("PNG (*.png)", "*.png"),
                        ]
    left_col = sg.Col([
                    [sg.Text("You are labeling [image_name]", font=('Any 15'), key="-IMAGETEXT-")],
                    [sg.Text(f"from folder {dir} .")],
                    [
                        sg.Text(f"Annotation Progress: i/n", key="-ANNOPROGRESS-"),
                        sg.ProgressBar(max_value=10, orientation="horizontal", bar_color=("green", "white"), size=(30, 10), key="-PBAR-"),
                    ],
                    [
                        sg.Text(f"Landmark Progress: i/n", key="-LMPROGRESS-"),
                        sg.ProgressBar(max_value=10, orientation="horizontal", bar_color=("green", "white"), size=(30, 10), key="-LBAR-"),
                    ],
                    [
                        sg.Table(values=[], key="-LMTABLE-", headings=["Id", "x", "y"], col_widths=column_width, max_col_width=column_width, auto_size_columns=False, justification="center", expand_y=True),
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
                        sg.Button("Redo Image", key='-REDO-'),
                        sg.Button("Next Image (Enter)", key='-NEXT-', bind_return_key=True)
                    ],
                    [sg.Graph(
                        canvas_size=(image_gap, image_gap),
                        graph_bottom_left=(0, 0),
                        graph_top_right=(image_gap, image_gap),
                        key="-GRAPH-",
                        change_submits=True,  # mouse click events
                        background_color='white'
                    )],
                    # [sg.Image(size=(image_gap, image_gap), key="-IMAGE-")],
                    [sg.Button('Take a break, continue later', button_color=("black", "lightyellow"))],
                ], size=(int(w/2), h), pad=(0,0))
    left_frame = sg.Frame("Input data",  [[left_col]])
    right_frame = sg.Frame("Image", [[right_col]])
    label_window = [[left_frame, right_frame]]
        
    window = sg.Window('Annotation Window', label_window, resizable=True, finalize=True)
    window.Maximize()
    # Create annotation csv file or use existing ones. 
    # [Ask user to use new csv file or not? In the future.]
    annotation_file = os.path.join(ANNOTATION, os.path.basename(dir) + ".csv")
    if not os.path.isfile(annotation_file):
        header = ["image_name"] + [f"{letter}{i}" for i in range(1, num_lm+1) for letter in ["x","y"]]
        df = pd.DataFrame(columns = header)
        df.to_csv(annotation_file, index = False)
    else:
        # Check whether number of landmark is compatible with existing csv.
        df = pd.read_csv(annotation_file, header=0)
        num_lm_fromfile = (len(df.columns) - 1) / 2
        if num_lm != num_lm_fromfile:
            delete_annot = alert(f"Error: Detected {int(num_lm_fromfile)} landmarks from annotation file, but your input is {num_lm}.\nIf you insist on changing the number of landmarks, we will delete the original annotation file.")
            if delete_annot:
                os.remove(annotation_file)
                popup("Annotation file deleted successfully.\nRun the program again to create a new annotation file.\nExited the program safely.")
            else:
                popup("Annotation file preserved.\nExited the program safely.")
            exit()
    # Get all image paths
    image_exts = [".jpg", ".png", ".jpeg"]
    image_paths = [os.path.basename(p) for p in os.listdir(dir) if os.path.splitext(p)[1].lower() in image_exts]
    total_image_num = len(image_paths)
    # Check which image haven't been annotated
    df = pd.read_csv(annotation_file, header=0)
    annotated_image_paths = list(df["image_name"])
    annotated_num = len(annotated_image_paths)
    image_paths = [p for p in image_paths if p not in annotated_image_paths]
    if len(image_paths) == 0:
        popup(f"Annotation for folder {dir} is already completed.\nPlease pick a new folder to annotate.", "info")
        window.close()
        front_page()
        return
    counter = 0
    lm_counter = 1
    window["-IMAGETEXT-"].Update(f"You are labeling {image_paths[counter]}")
    window["-ANNOPROGRESS-"].Update(f"Annotation Progress: {annotated_num + counter}/{total_image_num}")
    window["-LMPROGRESS-"].Update(f"Landmark Progress: 0/{num_lm}")
    window["-PBAR-"].update(current_count = annotated_num, max = total_image_num)
    window["-LBAR-"].update(current_count = 0, max = num_lm)
    # Load template image if exist
    if os.path.isfile(CACHE):
        with open(CACHE, "r") as f:
            data = json.load(f)
            if "-TEMPLATE-FILE-" in data:
                image = Image.open(data["-TEMPLATE-FILE-"])
                image.thumbnail(window["-TEMPLATE-IMG-"].Size)
                bio = io.BytesIO()
                image.save(bio, format="PNG")
                window["-TEMPLATE-IMG-"].update(filename=None,data=bio.getvalue())
                window["-TEMPLATE-FILE-"].update(data["-TEMPLATE-FILE-"])
    # Load the first image
    ori_w, ori_h = load_image(window, dir, image_paths[counter], image_gap)
    # Looping with click events
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
            break
        if event == '-GRAPH-':
            mouse = values['-GRAPH-']
            if mouse == (None, None):
                continue
            if lm_counter == num_lm + 1:
                popup(f"You've annotated the last landmark.\nPlease proceed to next image.", "info")
                continue
            # Detect click position (top-left origin)
            x, y = mouse[0], mouse[1]
            x = int(x * ori_w / image_gap)
            y = ori_h - int(y * ori_h / image_gap)
            # Update Table
            table = window["-LMTABLE-"]
            values = table.Values
            values.append([lm_counter, x, y])
            table.update(values = values)
            # Update landmark progress
            window["-LMPROGRESS-"].Update(f"Landmark Progress: {lm_counter}/{num_lm}")
            window["-LBAR-"].update(current_count = lm_counter, max = num_lm)
            # Plot point on image
            graph = window["-GRAPH-"]
            graph.draw_circle(mouse, 10, fill_color='lightgreen', line_color='darkgreen', line_width=2)
            graph.draw_text(lm_counter, mouse)
            lm_counter += 1
        elif event == '-NEXT-':
            next_button = window["-NEXT-"]
            # Validate landmark counter
            # Number of landmark detected wrong.
            if lm_counter != num_lm + 1:
                flag = alert("You have not done annotate this image yet.\n" \
                    + f"This image need {num_lm} landmarks but only {lm_counter-1} received.\n"\
                    + "If you wish to continue, this image will not be recorded where you can annotate it again by re-launch the program.\n" \
                    + "If you agree, you will skip to the next image, if not you will continue landmark the current image.")
                if not flag:
                    continue
                # Not the last image
                elif counter + 1 < len(image_paths):
                    # Load next image
                    counter += 1 # Increment image counter
                    lm_counter = 1 # Reset landmark counter to 1
                    renew_annotate(window, dir, image_paths[counter], image_gap, annotated_num, total_image_num, num_lm)
                # Last image
                else:
                    remain = total_image_num - annotated_num
                    popup(f"Annotation for folder {dir} is completed, but you've skipped {remain} images.\nKindly resume the program and finish them. ", "info")
                    window.close()
                    front_page()
            # Number of landmark detected correct. 
            else:
                # Record landmark into csv file
                img_name = image_paths[counter]
                values = window["-LMTABLE-"].Values
                row = [img_name] + [value[i] for value in values for i in (1,2)]
                df = pd.DataFrame([row])
                df.to_csv(annotation_file, mode='a', header=False, index=False)
                # Not the last image
                lm_counter = 1 # Reset landmark counter to 1
                annotated_num += 1 # Increment annotated count
                if counter + 1< len(image_paths):
                    # Load next image and renew window.
                    counter += 1
                    lm_counter = 1
                    renew_annotate(window, dir, image_paths[counter], image_gap, annotated_num, total_image_num, num_lm)
                # Last image
                else:
                    remain = total_image_num - annotated_num
                    if remain == 0:
                        window["-ANNOPROGRESS-"].Update(f"Annotation Progress: {total_image_num}/{total_image_num}")
                        window["-PBAR-"].update(current_count = total_image_num, max = total_image_num)
                        popup(f"Annotation for folder {dir} is completed.\nThank you for using this program.", "info")
                        window.close()
                        front_page()
                    else:
                        window["-PBAR-"].update(current_count = total_image_num, max = total_image_num)
                        popup(f"Annotation for folder {dir} is completed, but you've skipped {remain} images.\nKindly resume the program and finish them. ", "info")
                        window.close()
                        front_page()
        elif event == "-REDO-":
            lm_counter = 1
            renew_annotate(window, dir, image_paths[counter], image_gap, annotated_num, total_image_num, num_lm)
        elif event == "Load Template":
            filename = values["-TEMPLATE-FILE-"]
            if os.path.exists(filename):
                image = Image.open(values["-TEMPLATE-FILE-"])
                image.thumbnail(window["-TEMPLATE-IMG-"].Size)
                bio = io.BytesIO()
                image.save(bio, format="PNG")
                window["-TEMPLATE-IMG-"].update(filename=None,data=bio.getvalue())
                # Update cache file
                with open(CACHE, "r") as f:
                    data = json.load(f)
                data["-TEMPLATE-FILE-"] = filename
                with open(CACHE, "w") as f:
                    json.dump(data, f)
            else:
                popup("There is some issue with loading your template image.\nIn case you forgot, you need to first 'Browse' the image.")
        elif event == 'Take a break, continue later':
            window.close()
            front_page()
        
    window.close()

if __name__ == "__main__":
    # sg.theme_previewer()
    front_page()
