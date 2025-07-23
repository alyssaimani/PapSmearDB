import torch
import torch.nn as nn
import torch.nn.functional as F

from torchvision import transforms

from PIL import Image, ImageDraw
from lime import lime_image

import numpy as np
from skimage.segmentation import mark_boundaries

from tqdm.auto import tqdm

from os import listdir
from os.path import join
import geojson

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def get_image(path):
    # notes:
    # PIL reads as RGB, returns PIL Image object
    # cv2 reads as BGR, returns numpy array
    # better use PIL for direct RGB
    with open(path, 'rb') as f:
        with Image.open(f) as img:
            return img.convert('RGB') 

def get_resize_transform():
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
    ])
    return transform

def get_tensor_normalize_transform():
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
    transform = transforms.Compose([
        transforms.ToTensor(),
        normalize
    ])
    return transform

def get_preprocess_transform():
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])
    return transform

class DinoModelWrapper(nn.Module):
    def __init__(self, device):
        super(DinoModelWrapper, self).__init__()

        self.model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vits14').to(device)

        for param in self.model.parameters():
            param.requires_grad = False

        self.model.blocks[-1:].requires_grad_(True)
        self.model.norm.requires_grad_(True)
        self.model.head = torch.nn.Dropout(p=0.45)

        self.classification_head_1 = nn.Sequential(
            self.model,
            nn.Linear(384, 9)
        )

        self.classification_head_2 = nn.Sequential(
            self.model,
            nn.Linear(384, 4)
        )

    def forward(self, x, task):
        if task == 1:
            return self.classification_head_1(x)
        elif task == 2:
            return self.classification_head_2(x)
        else:
            raise ValueError("Invalid task ID")

def batch_predict(model, images, transform):
    model.eval()
    with torch.inference_mode():
        batch = torch.stack(tuple(transform(img) for img in images), dim=0)
        batch = batch.to(device)
        logits = model(batch, task=1) # task=1 for 9-class, task=2 for 4-class
        pred_probs = torch.softmax(logits, dim=1)
        pred_labels = torch.argmax(pred_probs, dim=1)

    return pred_probs.detach().cpu().numpy(), pred_labels.detach().cpu().numpy()

def batch_explanation(images):
    temps = []
    masks = []

    for img in images:
        explainer = lime_image.LimeImageExplainer()
        explanation = explainer.explain_instance(np.array(img),
                                                 batch_predict, # classification function
                                                 top_labels=4,
                                                 hide_color=0,
                                                 num_samples=1000) # number of images that will be sent to classification function
        temp, mask = explanation.get_image_and_mask(explanation.top_labels[0], 
                                                    positive_only=False,  
                                                    hide_rest=False)
        temps.append(temp)
        masks.append(mask)

    return temps, masks

def get_cropped_images(img_file, geojson_file):
    cropped_images = []

    img = np.asarray(get_image(img_file))
    with open(geojson_file) as f:
        gj = geojson.load(f)

    # iterate through feature (ROI annotations)
    for feature in gj['features']:
        label = feature['properties']['classification']['name']
        
        # get bounding box information
        bbox_corners = feature['geometry']['coordinates'][0][:-1]
        x_min, x_max = min(x for x, _ in bbox_corners), max(x for x, _ in bbox_corners)
        y_min, y_max = min(y for _, y in bbox_corners), max(y for _, y in bbox_corners)
        height, width = y_max - y_min, x_max - x_min

        # get cropped image (ROI)
        cropped_image = img[y_min:y_min+height, x_min:x_min+width, :]

        # if cropped image is not square (height=width), add zero padding on the lacking side
        if width < height:
            # zero pad the right of the cropped image if width is smaller than height
            padding = np.zeros((height, height-width, 3), dtype=np.uint8)
            cropped_image = np.hstack((cropped_image, padding))
        elif height < width:
            # zero pad the bottom of the cropped image if height is smaller than width
            padding = np.zeros((width-height, width, 3), dtype=np.uint8)
            cropped_image = np.vstack((cropped_image, padding))
        else:
            cropped_image = img.copy()

        # convert numpy array to PIL image for further preprocessing
        cropped_images.append(Image.fromarray(cropped_image.astype('uint8'), 'RGB'))
    
    return cropped_images


def get_bbox_corners(geojson_file):
    bbox = []

    with open(geojson_file) as f:
        gj = geojson.load(f)

    for feature in gj['features']:
        label = feature['properties']['classification']['name']

        bbox_corners = feature['geometry']['coordinates'][0][:-1]
        x_min, x_max = min(x for x, _ in bbox_corners), max(x for x, _ in bbox_corners)
        y_min, y_max = min(y for _, y in bbox_corners), max(y for _, y in bbox_corners)
        height, width = y_max - y_min, x_max - x_min
        
        bbox.append([x_min, y_min, width, height])

    return bbox

def draw_bounding_box_pil(img_file, geojson_file, show=False, out_file=None):
    bbox = get_bbox_corners(geojson_file)
    pil_image = get_image(img_file)
    draw = ImageDraw.Draw(pil_image)

    for bb in bbox:
        x_min, y_min, width, height = bb
        draw.rectangle([x_min, y_min, x_min+width, y_min+height], outline="red", width=5)

    if out_file:
        pil_image.save(out_file)

    if show:
        pil_image.show()
    return pil_image


if __name__ == "__main__":
    # load model
    MODEL_PATH = "media/best_model_multitask_part_4.pt"
    model = DinoModelWrapper(device=device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)

    for param in model.parameters():
        param.requires_grad = False
    model.eval()

    # test case for preprocessed images (ROIs, cropped and resized to 224x224)
    # test_dir = "./data/preprocessed/test/HSIL"

    # images = []
    # for path in listdir(test_dir):
    #     img = get_image(join(test_dir, path))
    #     images.append(img)

    # # does not need resizing to 224x224, available in get_tensor_normalize_transform()
    # _, pred_labels = batch_predict(model, images, transform=get_tensor_normalize_transform())
    # print(pred_labels)

    # test case for full images with annotations in geojson file
    img_file = "media/uploads/20x.jpg"
    geojson_file = img_file.replace('.jpg', '.geojson')

    # cropping a full image into ROIs based on bounding box annotations in geojson file
    # cropped_images = get_cropped_images(img_file, geojson_file)
    # print(cropped_images)

    # # needs resizing to 224x224, available in get_preprocess_transform()
    # _, pred_labels = batch_predict(model, cropped_images, transform=get_preprocess_transform())
    # print(pred_labels)