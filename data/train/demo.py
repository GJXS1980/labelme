
from ultralytics import YOLO

def main():
    model = YOLO('F:/vision_ws/demo/ultralytics/ultralytics/cfg/models/v8/boxes-seg.yaml')
    model.train(data='F:/vision_ws/demo/ultralytics/ultralytics/cfg/datasets/boxes-seg.yaml', epochs=500, imgsz=1280, batch=1, plots=True)

if __name__ == '__main__':
    main()
