from utils import *
from PIL import Image
import io
import os
import pandas as pd
import numpy as np
import json

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
        graph.DrawImage(data = data, location= (0, self.image_gap))
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
            image = Image.open(self.template_file)
            image.thumbnail(self.window["-TEMPLATE-IMG-"].Size)
            bio = io.BytesIO()
            image.save(bio, format="PNG")
            self.window["-TEMPLATE-IMG-"].update(filename=None,data=bio.getvalue())
            self.window["-TEMPLATE-FILE-"].update(self.template_file)

    def window_init(self):
        # renew window
        self.renew_annotate()
        # Load template file if exists
        self.load_template()

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
        y = ori_h - int(y * ori_h / self.image_gap) # Because PySimpleGUI graph use bottom-left origin setting.
        return x,y

    def plot_point(self, mouse):
        if not self.dynamic_lm and self.num_lm == self.total_num_lm:
            sg.popup(f"You've annotated the last landmark.\nPlease proceed to next image.")
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
                sg.popup("This is the last image.\nTo safely exit this program, please click the Save button.")
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
    
    def unfinish_images_prompt(self):
        response = sg.popup_yes_no("All images have been annotated. Please check for unfinished images. Do you wish to quit now? ")
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
        graph.DrawImage(data = data, location= (0, self.image_gap))
        # Plot previous points
        graph = self.window["-GRAPH-"]
        for landmark in self.real_mouses:
            graph.draw_circle(landmark[1:], 10, fill_color='lightgreen', line_color='darkgreen', line_width=2)
            graph.draw_text(landmark[0], landmark[1:])
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
        response = sg.popup_yes_no(f"Annotation file saved! View it in {csv_filename}.\nDo you wish to quit?")
        return response
    
    def popup_with_confirm_and_ignore(self, message: str):
        if self.ignore_warning1:
            return "Yes"
        layout = [
            [sg.Text(message)],
            [sg.Checkbox("I understand, do not show this warning again.", key="-CHECK-")],
            [sg.Button("OK"), sg.Button("Cancel")]
        ]
        window = sg.Window("Warning", layout)
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
