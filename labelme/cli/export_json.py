import argparse
import base64
import json
import os
import os.path as osp

import imgviz
import PIL.Image
import PIL.ImageDraw
from labelme import utils
from labelme.logger import logger

import random
import shutil
from tqdm import tqdm
import math
import numpy as np
import cv2

class ConvertManager(object):
    def __init__(self):
        pass
 
    def base64_to_numpy(self, img_bs64):
        img_bs64 = base64.b64decode(img_bs64)
        img_array = np.frombuffer(img_bs64, np.uint8)
        cv2_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return cv2_img
 
    @classmethod
    def load_labels(cls, name_file):
        '''
        load names from file.one name one line
        :param name_file:
        :return:
        '''
        with open(name_file, 'r') as f:
            lines = f.read().rstrip('\n').split('\n')
        return lines
 
    def get_class_names_from_all_json(self, json_dir):
        classnames = []
        for file in os.listdir(json_dir):
            if not file.endswith('.json'):
                continue
            with open(os.path.join(json_dir, file), 'r', encoding='utf-8') as f:
                data_dict = json.load(f)
                for shape in data_dict['shapes']:
                    if not shape['label'] in classnames:
                        classnames.append(shape['label'])
        return classnames
 
    def create_save_dir(self, save_dir):
        images_dir = os.path.join(save_dir, 'images')
        labels_dir = os.path.join(save_dir, 'labels')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            os.mkdir(images_dir)
            os.mkdir(labels_dir)
        else:
            if not os.path.exists(images_dir):
                os.mkdir(images_dir)
            if not os.path.exists(labels_dir):
                os.mkdir(labels_dir)
        return images_dir + os.sep, labels_dir + os.sep
 
    def save_list(self, data_list, save_file):
        with open(save_file, 'w') as f:
            f.write('\n'.join(data_list))
 
    def __rectangle_points_to_polygon(self, points):
        xmin = 0
        ymin = 0
        xmax = 0
        ymax = 0
        if points[0][0] > points[1][0]:
            xmax = points[0][0]
            ymax = points[0][1]
            xmin = points[1][0]
            ymin = points[1][1]
        else:
            xmax = points[1][0]
            ymax = points[1][1]
            xmin = points[0][0]
            ymin = points[0][1]
        return [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]]
 
    def convert_dataset(self, json_dir, json_list, images_dir, labels_dir, names, save_mode='train'):
        images_dir = os.path.join(images_dir, save_mode)+os.sep
        labels_dir = os.path.join(labels_dir, save_mode)+os.sep
        if not os.path.exists(images_dir):
            os.mkdir(images_dir)
        if not os.path.exists(labels_dir):
            os.mkdir(labels_dir)
        for file in tqdm(json_list):
            with open(os.path.join(json_dir, file), 'r', encoding='utf-8') as f:
                data_dict = json.load(f)
            image_file = os.path.join(json_dir, os.path.basename(data_dict['imagePath']))
            if os.path.exists(image_file):
                shutil.copyfile(image_file, images_dir + os.path.basename(image_file))
            else:
                imageData = data_dict.get('imageData')
                if not imageData:
                    imageData = base64.b64encode(imageData).decode('utf-8')
                    img = self.img_b64_to_arr(imageData)
                    PIL.Image.fromarray(img).save(images_dir + file[:-4] + 'png')
            # convert to txt
            width = data_dict['imageWidth']
            height = data_dict['imageHeight']
            line_list = []
            for shape in data_dict['shapes']:
                data_list = []
                data_list.append(str(names.index(shape['label'])))
                if shape['shape_type'] == 'rectangle':
                    points = self.__rectangle_points_to_polygon(shape['points'])
                    for point in points:
                        data_list.append(str(point[0] / width))
                        data_list.append(str(point[1] / height))
 
 
                elif shape['shape_type'] == 'polygon':
                    points = shape['points']
                    for point in points:
                        data_list.append(str(point[0] / width))
                        data_list.append(str(point[1] / height))
                line_list.append(' '.join(data_list))
 
            self.save_list(line_list, labels_dir + file[:-4] + "txt")
 
    def split_train_val_test_dataset(self, file_list, train_ratio=0.9, trainval_ratio=0.9, need_test_dataset=False,
                                     shuffle_list=True):
        if shuffle_list:
            random.shuffle(file_list)
        total_file_count = len(file_list)
        train_list = []
        val_list = []
        test_list = []
        if need_test_dataset:
            trainval_count = int(total_file_count * trainval_ratio)
            trainval_list = file_list[:trainval_count]
            test_list = file_list[trainval_count:]
            train_count = int(train_ratio * len(trainval_list))
            train_list = trainval_list[:train_count]
            val_list = trainval_list[train_count:]
        else:
            train_count = int(train_ratio * total_file_count)
            train_list = file_list[:train_count]
            val_list = file_list[train_count:]
        return train_list, val_list, test_list
 
    def start(self, json_dir, save_dir, names=None, train_ratio=0.9):
        images_dir, labels_dir = self.create_save_dir(save_dir)
        if names is None or len(names) == 0:
            print('class names will load from all json file')
            names = self.get_class_names_from_all_json(json_dir)
        print('find {} class names :'.format(len(names)), names)
        if len(names) == 0:
            return
 
        self.save_list(names, os.path.join(save_dir, 'labels.txt'))
        print('start convert')
        all_json_list = []
        for file in os.listdir(json_dir):
            if not file.endswith('.json'):
                continue
            all_json_list.append(file)
        train_list, val_list, test_list = self.split_train_val_test_dataset(all_json_list, train_ratio)
        self.convert_dataset(json_dir, train_list, images_dir, labels_dir, names, 'train')
        self.convert_dataset(json_dir, val_list, images_dir, labels_dir, names, 'val')
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")
    parser.add_argument("-o", "--out", default=None)
    args = parser.parse_args()

    json_file = args.json_file

    if args.out is None:
        out_dir = osp.splitext(osp.basename(json_file))[0]
        out_dir = osp.join(osp.dirname(json_file), out_dir)
    else:
        out_dir = args.out
    if not osp.exists(out_dir):
        os.mkdir(out_dir)

    data = json.load(open(json_file))
    imageData = data.get("imageData")

    if not imageData:
        imagePath = os.path.join(os.path.dirname(json_file), data["imagePath"])
        with open(imagePath, "rb") as f:
            imageData = f.read()
            imageData = base64.b64encode(imageData).decode("utf-8")
    img = utils.img_b64_to_arr(imageData)

    label_name_to_value = {"_background_": 0}
    for shape in sorted(data["shapes"], key=lambda x: x["label"]):
        label_name = shape["label"]
        if label_name in label_name_to_value:
            label_value = label_name_to_value[label_name]
        else:
            label_value = len(label_name_to_value)
            label_name_to_value[label_name] = label_value
    lbl, _ = utils.shapes_to_label(img.shape, data["shapes"], label_name_to_value)

    label_names = [None] * (max(label_name_to_value.values()) + 1)
    for name, value in label_name_to_value.items():
        label_names[value] = name

    lbl_viz = imgviz.label2rgb(
        lbl, imgviz.asgray(img), label_names=label_names, loc="rb"
    )

    PIL.Image.fromarray(img).save(osp.join(out_dir, "img.png"))
    utils.lblsave(osp.join(out_dir, "label.png"), lbl)
    PIL.Image.fromarray(lbl_viz).save(osp.join(out_dir, "label_viz.png"))

    with open(osp.join(out_dir, "label_names.txt"), "w") as f:
        for lbl_name in label_names:
            f.write(lbl_name + "\n")

    logger.info("Saved to: {}".format(out_dir))

    # # json转yolo格式
    # cm = ConvertManager()
    # cm.start(out_dir, out_dir)


if __name__ == "__main__":
    main()
