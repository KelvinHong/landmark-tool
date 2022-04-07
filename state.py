from tkinter.tix import WINDOW
from urllib.parse import _NetlocResultMixinBytes
from utils import *
from PIL import Image
import io
import os
import pandas as pd
import numpy as np
import json
import screeninfo
# Detect double monitor
monitors = screeninfo.get_monitors()
if len(monitors) >= 2:
    w1, h1 = monitors[0].width, monitors[0].height
    w2, h2 = monitors[1].width, monitors[1].height
    WINDOW_LOC = (w1 + int(w2/8), int(h1/8))
else:
    WINDOW_LOC = (None, None)
# The StateMachine functions is to keep track of the graph
# and to keep function call and future modification easier to implement.
# The StateMachine functions are a bit repeat themselves, 
# not very elegant. 
# Considering cleaning them in the future.
class WindowStateMachine():
    def __init__(self, window, data: dict = {}):
        self.window = window
        self.real_mouses = []
        self.ignore_warning1 = False
        # All data 
        self.total_num_images = data['total_num_images']
        self.dir = data["dir"]
        self.annotation_json = data["annotation_json"]
        self.all_image_rel_paths = data["all_image_rel_paths"]
        self.pointer = data["pointer"]
        self.image_gap = data["image_gap"]
        self.column_width = data["column_width"]
        self.dynamic_lm = data["dynamic_lm"]
        self.shift_mode = data["shift_mode"]
        self.store_mouse = None # For storing mouse location in shift_mode
        # Load num_lm correctly if user have annotated in last session
        image_name = self.all_image_rel_paths[self.pointer]
        with open(self.annotation_json, "r") as f:
            d = json.load(f)
            if image_name in d:
                self.num_lm = len(d[image_name]["xy"])
            else:
                self.num_lm = 0
        # Take total_num_lm only when dynamic_lm setting is off.
        if not self.dynamic_lm:
            self.total_num_lm = data["total_num_lm"]
        # Take template_file if it is provided
        if "template_file" in data:
            self.template_file = data["template_file"]
        

    def load_image(self, request = None):
        """
        Load Image and its landmarks (if exist)
        Update Image w and h on GUI
        Update Table on GUI
        Update self.real_mouses
        """
        # Renew image name.
        img_name = self.all_image_rel_paths[self.pointer]
        self.window["-IMAGETEXT-"].Update(f"You are labeling {img_name}")
        # Load current image for user to annotate
        im = Image.open(os.path.join(self.dir, img_name))
        w, h = im.size
        im = im.resize((self.image_gap, self.image_gap), resample = Image.BICUBIC)
        with io.BytesIO() as output:
            im.save(output, format="PNG")
            data = output.getvalue()
        # Load image to graph
        graph = self.window["-GRAPH-"]
        graph.DrawImage(data = data, location= (0, 0))
        # If request is redo, do not load from JSON
        if request == "redo":
            self.num_lm = 0
            self.real_mouses = []
            table_values = []
        else:
            # Load points from JSON file if exist
            with open(self.annotation_json, "r") as f:
                data = json.load(f)
                if img_name in data:
                    self.num_lm = len(data[img_name]["xy"])
                    self.real_mouses = [[i+1, *data[img_name]["mouse_xy"][i]]for i in range(self.num_lm)]
                    table_values = [[i+1, *data[img_name]["xy"][i]]for i in range(self.num_lm)]
                else:
                    self.num_lm = 0
                    self.real_mouses = []
                    table_values = []
        # Update table
        self.window["-LMTABLE-"].update(values = table_values)
        # Show landmarks on graph
        for i in range(self.num_lm):
            graph.draw_circle(self.real_mouses[i][1:], 10, fill_color='lightgreen', line_color='darkgreen', line_width=2)
            graph.draw_text(self.real_mouses[i][0], self.real_mouses[i][1:])
        
        # Update image width height info
        self.image_original = [w, h]
        self.window["-IMAGE-INFO-"].Update(f"W = {w}px, H = {h}px", visible=True)
        return img_name
    
    def load_template(self):
        if hasattr(self, "template_file"):
            try:
                image = Image.open(self.template_file)
            except:
                sg.popup("The file you provided is not an image file. ", location=WINDOW_LOC)
                return False
            image.thumbnail(self.window["-TEMPLATE-IMG-"].Size)
            bio = io.BytesIO()
            image.save(bio, format="PNG")
            self.window["-TEMPLATE-IMG-"].update(filename=None,data=bio.getvalue())
            self.window["-TEMPLATE-FILE-"].update(self.template_file)
            return True
            
    def window_init(self):
        # Fill mouse_xy in json file
        self.fill_json()
        # renew window
        self.renew_annotate()
        # Load template file if exists
        self.load_template()

    def fill_json(self):
        with open(self.annotation_json, "r") as f:
            data = json.load(f)
        for img_name, coor_info in data.items():
            if coor_info["xy"] == []:
                data[img_name]["mouse_xy"] = []
                continue
            im = Image.open(os.path.join(self.dir, img_name))
            w, h = im.size
            np_coorinfo = np.array(coor_info["xy"]) # Size (n, 2)
            mouses = np.zeros(np_coorinfo.shape)
            mouses[:, 0] = (np_coorinfo[:, 0] * self.image_gap / w).round()
            mouses[:, 1] = (np_coorinfo[:, 1] * self.image_gap / h).round()
            data[img_name]["mouse_xy"] = list(mouses)
        pretty_dump(data, self.annotation_json)

    def renew_annotate(self, request = None):
        """
            [
                Update Image text
                Update Table
                Update image in Graph
                Plot landmarks if exist
            ] these done in load_image.
            Update annotated image, its progress bar
            Update Landmark and its progress bar (if not dynamic lm)
        """
        img_path = self.load_image(request = request)
        total_image_num = self.total_num_images
        # Disable arrow button if first or last
        # Next button style
        if self.pointer == total_image_num - 1:
            self.window['-NEXT-'].update(disabled=True)
        else:
            self.window['-NEXT-'].update(disabled=False)
        # Prev button style
        if self.pointer == 0:
            self.window['-PREV-'].update(disabled=True)
        else:
            self.window['-PREV-'].update(disabled=False)
        if not self.dynamic_lm:
            self.window["-LMPROGRESS-"].update(f"Landmark Progress: {self.num_lm}/{self.total_num_lm}")
            self.window["-LBAR-"].update(current_count = self.num_lm, max = self.total_num_lm)
        else:
            self.window["-LMPROGRESS-"].update(f"Landmark Progress: {self.num_lm}")
        
        self.window["-ANNOPROGRESS-"].update(f"Annotation Progress: {self.pointer}/{total_image_num}")
        self.window["-PBAR-"].update(current_count = self.pointer, max = total_image_num)
        
    def mouse_to_xy(self, mouse):
        x, y = mouse[0], mouse[1]
        ori_w, ori_h = self.image_original
        x = int(x * ori_w / self.image_gap)
        y = int(y * ori_h / self.image_gap) 
        return x,y
    
    def xy_to_mouse(self, xy):
        ori_w, ori_h = self.image_original
        mouse_x = int(xy[0] * self.image_gap / ori_w)
        mouse_y = int(xy[1] * self.image_gap / ori_h)
        return mouse_x, mouse_y

    def plot_point(self, mouse):
        if not self.dynamic_lm and self.num_lm == self.total_num_lm:
            sg.popup(f"You've annotated the last landmark.\nPlease proceed to next image.", location = WINDOW_LOC)
            return 
        x, y = self.mouse_to_xy(mouse)
        # num_lm increment
        self.num_lm += 1
        self.real_mouses.append([self.num_lm, *mouse])
        # Update Table
        table = self.window["-LMTABLE-"]
        values = table.Values
        values.append([self.num_lm, x, y])
        table.update(values = values)
        # Update landmark progress
        if self.dynamic_lm:
            self.window["-LMPROGRESS-"].Update(f"Landmark Progress: {self.num_lm}")
        else:
            self.window["-LMPROGRESS-"].Update(f"Landmark Progress: {self.num_lm}/{self.total_num_lm}")
            self.window["-LBAR-"].update(current_count = self.num_lm, max = self.total_num_lm)
        # Plot point on image
        graph = self.window["-GRAPH-"]
        graph.draw_circle(mouse, 10, fill_color='lightgreen', line_color='darkgreen', line_width=2)
        graph.draw_text(self.num_lm, mouse)
    
    def next_image(self):
        # If Dynamic landmark, shouldn't prevent user to next image.
        if self.dynamic_lm:
            # Save current landmark progress into json file
            self.record()
            # Update window
            if self.pointer + 1 < len(self.all_image_rel_paths):
                # Load next image
                self.pointer += 1 
                self.renew_annotate()
            else:
                self.window["-ANNOPROGRESS-"].update(f"Annotation Progress: {self.pointer+1}/{self.total_num_images}")
                self.window["-PBAR-"].update(current_count = self.pointer+1, max = self.total_num_images)
                sg.popup("This is the last image.\nTo safely exit this program, please click the Save button.", location=WINDOW_LOC)
                return 
        # Landmark insufficient
        elif self.num_lm != self.total_num_lm:
            flag = self.popup_with_confirm_and_ignore("You have not done annotate this image yet.\n" \
                + f"This image need {self.total_num_lm} landmarks but only {self.num_lm} received.\n"\
                + "However, you can still continue where all data will be saved." \
                + "Do you wish to continue?")
            if flag == "No" or flag is None: return
            
            # When flag == Yes, save data into json
            self.record()
            # Not the last image
            if self.pointer + 1 < len(self.all_image_rel_paths):
                # Load next image
                self.pointer += 1 
                self.renew_annotate()
            # Last image
            else:
                self.window["-ANNOPROGRESS-"].update(f"Annotation Progress: {self.pointer+1}/{self.total_num_images}")
                self.window["-PBAR-"].update(current_count = self.pointer+1, max = self.total_num_images)
                return self.unfinish_images_prompt() # Return "Home" if user agree to exit
        # Number of landmark detected correct
        else:
            # Record landmark into json file
            self.record()
            # Not the last image
            if self.pointer + 1 < len(self.all_image_rel_paths):
                # Load next image and renew window.
                self.pointer += 1
                self.renew_annotate()
            # Last image
            else:
                self.window["-ANNOPROGRESS-"].update(f"Annotation Progress: {self.pointer+1}/{self.total_num_images}")
                self.window["-PBAR-"].update(current_count = self.pointer+1, max = self.total_num_images)
                return self.unfinish_images_prompt()
        # If Last image, disable next button
        if self.pointer == self.total_num_images - 1:
            self.window['-NEXT-'].update(disabled=True)
        # Coming from first to second image, enable prev button
        if self.pointer == 1:
            self.window['-PREV-'].update(disabled=False)
    
    def unfinish_images_prompt(self):
        response = sg.popup_yes_no("All images have been annotated. Please check for unfinished images. Do you wish to quit now? ", location=WINDOW_LOC)
        if response == "Yes":
            response2 = self.save_session()
            if response2 == "Yes":
                return "Home"

    def record(self):
        img_name = self.all_image_rel_paths[self.pointer]
        table_values = self.window["-LMTABLE-"].Values
        mouse_values = self.real_mouses
        # Load json 
        with open(self.annotation_json, "r") as f:
            data = json.load(f)
        values_dict = {
            "xy": [value[1:] for value in table_values],
            "mouse_xy": [value[1:] for value in mouse_values]
        }
        data.update({img_name: values_dict})
        # Save to json
        pretty_dump(data, self.annotation_json)

    def renew_graph(self):
        img_name = self.all_image_rel_paths[self.pointer]
        # Load current image for user to annotate
        im = Image.open(os.path.join(self.dir, img_name))
        w, h = im.size
        im = im.resize((self.image_gap, self.image_gap), resample = Image.BICUBIC)
        with io.BytesIO() as output:
            im.save(output, format="PNG")
            data = output.getvalue()
        # Load image to graph
        graph = self.window["-GRAPH-"]
        graph.DrawImage(data = data, location= (0, 0))
        for landmark in self.real_mouses:
            graph.draw_circle(tuple(landmark[1:]), 10, fill_color='lightgreen', line_color='darkgreen', line_width=2)
            graph.draw_text(landmark[0], tuple(landmark[1:]))

    def table_prompt(self, message: str):
        self.window["-TABLEPROMPT-"].Update(message, visible=True)

    def undo_landmark(self):
        if self.num_lm == 0:
            # Cannot undo when no landmarks
            return 
        # Decrease number of landmark
        self.num_lm -= 1
        # Pop the mouse location in view
        self.real_mouses.pop() 
        # Pop the real landmark coordinate, then update
        values = self.window["-LMTABLE-"].Values
        last_landmark = values.pop() 
        self.window["-LMTABLE-"].Update(values = values)
        # Prompt removal below table
        self.table_prompt(f"Landmark Number {last_landmark[0]} removed.")
        # Load current image for user to annotate
        img_name = self.all_image_rel_paths[self.pointer]
        im = Image.open(os.path.join(self.dir, img_name))
        w, h = im.size
        im = im.resize((self.image_gap, self.image_gap), resample = Image.BICUBIC)
        with io.BytesIO() as output:
            im.save(output, format="PNG")
            data = output.getvalue()
        # Load image to graph
        graph = self.window["-GRAPH-"]
        graph.DrawImage(data = data, location= (0, 0))
        # Plot previous points
        self.renew_graph()
        
        # Update landmark progress text and bar.
        if self.dynamic_lm:
            self.window["-LMPROGRESS-"].Update(f"Landmark Progress: {self.num_lm}")    
        else:
            self.window["-LMPROGRESS-"].Update(f"Landmark Progress: {self.num_lm}/{self.total_num_lm}")
            self.window["-LBAR-"].Update(current_count = self.num_lm, max = self.total_num_lm)
        
    def prev_image(self):
        # Cannot prev if first image
        if self.pointer == 0:
            return 
        # Record landmark to wait for user return.
        self.record()
        # Renew windows on previous image
        self.pointer -= 1
        self.renew_annotate()
        # If First image, disable next button
        if self.pointer == 0:
            self.window['-PREV-'].update(disabled=True)
        # Coming from last to second last, enable next
        if self.pointer == self.total_num_images - 2:
            self.window['-NEXT-'].update(disabled=False)

    def generate_csv(self):
        with open(self.annotation_json, "r") as f:
            Data = json.load(f)
        # In dynamic lm case, get max number of landmarks
        if self.dynamic_lm:
            max_lm = 0
            for key, value in Data.items():
                max_lm = max(max_lm, len(value["xy"]))
        else:
            max_lm = self.total_num_lm
        # Following self.all_image_rel_paths
        compact_Data = []
        for imgrel in self.all_image_rel_paths:
            if imgrel in Data:
                xy = [int(j) for sub in Data[imgrel]["xy"] for j in sub]
                num_nan = 2 * max_lm - len(xy)
                xy += [np.nan] * num_nan
                one_row = [imgrel] + xy
                compact_Data.append(one_row)
        # Save to csv
        df = pd.DataFrame(data = compact_Data)
        df.columns = ["image_name"] + [letter + str(i) for i in range(1, max_lm+1) for letter in ["x", "y"]]
        csv_filename = os.path.splitext(self.annotation_json)[0] + ".csv"
        df.to_csv(csv_filename, index=False)
        return csv_filename

    def cancel_shift(self):
        graph = self.window["-GRAPH-"]
        graph.draw_circle(tuple(self.store_mouse[1]), 10, fill_color='lightgreen', line_color='green', line_width=2)
        graph.draw_text(self.store_mouse[0], tuple(self.store_mouse[1]))
        number = self.store_mouse[0]
        table = self.window['-LMTABLE-']
        table.update(row_colors = [[number-1, table.BackgroundColor]])
        self.store_mouse = None
        self.window['-SHIFT-PROMPT-'].Update("Choose a point to move", visible=True) 

    def move_point(self, mouse):
        # Assuming mouse is not (None, None)

        # No landmark on the graph, return immediately
        if self.num_lm == 0:
            # Clear mouse location 
            self.store_mouse = None
            return 
        # When store_mouse is None find nearest point based on mouse location 
        if self.store_mouse is None:
            mouses = np.array([real_mouse[1:] for real_mouse in self.real_mouses]) # Shape (N, 2)
            diffs = mouses - np.array(mouse)
            # Find nearest point
            indmin = np.argmin(diffs[:, 0] ** 2 + diffs[:, 1] ** 2)
            # Change the landmark color and store into store_mouse
            self.store_mouse = (indmin+1, mouses[indmin])
            # Change the row color of table
            self.window['-LMTABLE-'].Update(row_colors=[[indmin,'#6A0DAD']])
            # Plot point on image
            graph = self.window["-GRAPH-"]
            graph.draw_circle(tuple(self.store_mouse[1]), 10, fill_color='purple', line_color='#6A0DAD', line_width=2)
            graph.draw_text(self.store_mouse[0], tuple(self.store_mouse[1]), color="white")
            # Update prompt
            self.window['-SHIFT-PROMPT-'].Update("Choose a destination\nEsc to cancel", visible=True) 
        # When store_mouse is not None, use its index to place new point.
        else:
            number = self.store_mouse[0]
            # self.real_mouses and renew graph and table
            self.real_mouses[number-1] = [number, *mouse]
            self.renew_graph()
            x,y = self.mouse_to_xy(mouse)
            table = self.window["-LMTABLE-"]
            values = table.Values
            values[number-1] = [number, x, y]
            table.update(values = values, row_colors = [[number-1, table.BackgroundColor]])
            # Update prompt
            self.window['-SHIFT-PROMPT-'].Update("Choose a point to move", visible=True) 
            # Clear store_mouse
            self.store_mouse = None
            
            
            




    def save_session(self):
        # Record where user at
        with open(CACHE, "r") as f:
            D = json.load(f)
        D["pointer"] = self.pointer
        pretty_dump(D, CACHE)
        # Record landmark to json file
        self.record()
        # Convert json file into csv file
        csv_filename = self.generate_csv()
        response = sg.popup_yes_no(f"Annotation file saved! View it in {csv_filename}.\nDo you wish to quit?", location=WINDOW_LOC)
        return response
    
    def popup_with_confirm_and_ignore(self, message: str):
        if self.ignore_warning1:
            return "Yes"
        layout = [
            [sg.Text(message)], 
            [sg.Checkbox("I understand, do not show this warning again.", key="-CHECK-")],
            [sg.Button("OK"), sg.Button("Cancel")]
        ]
        window = sg.Window("Warning", layout, location=WINDOW_LOC)
        while True:
            event, values = window.read()
            if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
                break
            elif event == "OK":
                if values["-CHECK-"]:
                    self.ignore_warning1 = True
                window.close()
                return "Yes"
            elif event == "Cancel":
                if values["-CHECK-"]:
                    self.ignore_warning1 = True
                window.close()
                return "No"
