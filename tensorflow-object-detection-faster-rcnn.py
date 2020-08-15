#!/usr/bin/env python
# coding: utf-8

# In[1]:


get_ipython().system('pip install tensorflow_gpu==1.15')


# ## Configs and Hyperparameters
# 
# Support a variety of models, you can find more pretrained model from [Tensorflow detection model zoo: COCO-trained models](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/detection_model_zoo.md#coco-trained-models), as well as their pipline config files in [object_detection/samples/configs/](https://github.com/tensorflow/models/tree/master/research/object_detection/samples/configs).

# In[ ]:


# If you forked the repo, you can replace the link.
repo_url = 'https://github.com/roboflow-ai/tensorflow-object-detection-faster-rcnn'

# Number of training steps - 1000 will train very quickly, but more steps will increase accuracy.
num_steps = 5000  # 200000 to improve

# Number of evaluation steps.
#num_eval_steps = 50

MODELS_CONFIG = {
        'faster_rcnn_inception_v2': {
        'model_name': 'faster_rcnn_inception_v2_coco_2018_01_28',
        'pipeline_file': 'demo.config',
        'batch_size': 1
    }
}

# Pick the model you want to use
# Select a model in `MODELS_CONFIG`.
selected_model = 'faster_rcnn_inception_v2'

# Name of the object detection model to use.
MODEL = MODELS_CONFIG[selected_model]['model_name']

# Name of the pipline file in tensorflow object detection API.
pipeline_file = MODELS_CONFIG[selected_model]['pipeline_file']

# Training batch size fits in Colabe's Tesla K80 GPU memory for selected model.
batch_size = MODELS_CONFIG[selected_model]['batch_size']


# ## Clone the `tensorflow-object-detection` repository or your fork.

# In[3]:


import os

get_ipython().run_line_magic('cd', '/content')

repo_dir_path = os.path.abspath(os.path.join('.', os.path.basename(repo_url)))

get_ipython().system('git clone {repo_url}')
get_ipython().run_line_magic('cd', '{repo_dir_path}')
get_ipython().system('git pull')


# In[5]:


get_ipython().system('pip install tf_slim')


# ## Install required packages

# In[6]:


get_ipython().run_line_magic('cd', '/content')
get_ipython().system('git clone --quiet https://github.com/tensorflow/models.git')

get_ipython().system('apt-get install -qq protobuf-compiler python-pil python-lxml python-tk')

get_ipython().system('pip install -q Cython contextlib2 pillow lxml matplotlib')

get_ipython().system('pip install -q pycocotools')

get_ipython().run_line_magic('cd', '/content/models/research')
get_ipython().system('protoc object_detection/protos/*.proto --python_out=.')

import os
os.environ['PYTHONPATH'] += ':/content/models/research/:/content/models/research/slim/'

get_ipython().system('python object_detection/builders/model_builder_test.py')


# ## Prepare `tfrecord` files
# 
# Roboflow automatically creates our TFRecord and label_map files that we need!
# 
# **Generating your own TFRecords the only step you need to change for your own custom dataset.**
# 
# Because we need one TFRecord file for our training data, and one TFRecord file for our test data, we'll create two separate datasets in Roboflow and generate one set of TFRecords for each.
# 
# To create a dataset in Roboflow and generate TFRecords, follow [this step-by-step guide](https://blog.roboflow.ai/getting-started-with-roboflow/).

# In[7]:


get_ipython().run_line_magic('cd', '/content/tensorflow-object-detection-faster-rcnn/data')


# In[ ]:


# NOTE: Update these TFRecord names from "cells" and "cells_label_map" to your files!
train_record_fname = '/content/tensorflow-object-detection-faster-rcnn/data/data.record'
label_map_pbtxt_fname = '/content/tensorflow-object-detection-faster-rcnn/data/demo.pbtxt'


# ## Download base model

# In[9]:


get_ipython().run_line_magic('cd', '/content/models/research')

import os
import shutil
import glob
import urllib.request
import tarfile
MODEL_FILE = MODEL + '.tar.gz'
DOWNLOAD_BASE = 'http://download.tensorflow.org/models/object_detection/'
DEST_DIR = '/content/models/research/pretrained_model'

if not (os.path.exists(MODEL_FILE)):
    urllib.request.urlretrieve(DOWNLOAD_BASE + MODEL_FILE, MODEL_FILE)

tar = tarfile.open(MODEL_FILE)
tar.extractall()
tar.close()

os.remove(MODEL_FILE)
if (os.path.exists(DEST_DIR)):
    shutil.rmtree(DEST_DIR)
os.rename(MODEL, DEST_DIR)


# In[ ]:


get_ipython().system('echo {DEST_DIR}')
get_ipython().system('ls -alh {DEST_DIR}')


# In[15]:


fine_tune_checkpoint = os.path.join(DEST_DIR, "model.ckpt")
fine_tune_checkpoint


# ## Configuring a Training Pipeline

# In[28]:


import os
pipeline_fname = os.path.join('/content/models/research/object_detection/samples/configs/', pipeline_file)
print(pipeline_fname)

assert os.path.isfile(pipeline_fname), '`{}` not exist'.format(pipeline_fname)


# In[ ]:


def get_num_classes(pbtxt_fname):
    from object_detection.utils import label_map_util
    label_map = label_map_util.load_labelmap(pbtxt_fname)
    categories = label_map_util.convert_label_map_to_categories(
        label_map, max_num_classes=90, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)
    return len(category_index.keys())


# In[ ]:


import re

num_classes = get_num_classes(label_map_pbtxt_fname)
with open(pipeline_fname) as f:
    s = f.read()
with open(pipeline_fname, 'w') as f:
    
    # fine_tune_checkpoint
    s = re.sub('fine_tune_checkpoint: ".*?"',
               'fine_tune_checkpoint: "{}"'.format(fine_tune_checkpoint), s)
    
    # tfrecord files train and test.
    s = re.sub(
        '(input_path: ".*?)(train.record)(.*?")', 'input_path: "{}"'.format(train_record_fname), s)
    
    # label_map_path
    s = re.sub(
        'label_map_path: ".*?"', 'label_map_path: "{}"'.format(label_map_pbtxt_fname), s)

    # Set training batch_size.
    s = re.sub('batch_size: [0-9]+',
               'batch_size: {}'.format(batch_size), s)

    # Set training steps, num_steps
    s = re.sub('num_steps: [0-9]+',
               'num_steps: {}'.format(num_steps), s)
    
    # Set number of classes num_classes.
    s = re.sub('num_classes: [0-9]+',
               'num_classes: {}'.format(num_classes), s)
    f.write(s)


# In[ ]:


get_ipython().system('cat {pipeline_fname}')


# In[22]:


pwd


# In[ ]:


train_dir = 'training/'
# Optionally remove content in output model directory to fresh start.
get_ipython().system('rm -rf {train_dir}')
os.makedirs(train_dir, exist_ok=True)


# In[30]:


pwd


# ## Train the model

# In[24]:


print("Training the model")


# In[33]:


get_ipython().system('python /content/models/research/object_detection/legacy/train.py --pipeline_config_path=/content/models/research/object_detection/samples/configs/demo.config --train_dir=/content/models/research/training/')


# In[34]:


get_ipython().system('ls {train_dir}')


# ## Exporting a Trained Inference Graph
# Once your training job is complete, you need to extract the newly trained inference graph, which will be later used to perform the object detection. This can be done as follows:

# In[35]:


import re
import numpy as np

output_directory = './fine_tuned_model'

lst = os.listdir(train_dir)
lst = [l for l in lst if 'model.ckpt-' in l and '.meta' in l]
steps=np.array([int(re.findall('\d+', l)[0]) for l in lst])
last_model = lst[steps.argmax()].replace('.meta', '')

last_model_path = os.path.join(train_dir, last_model)
print(last_model_path)
get_ipython().system('python /content/models/research/object_detection/export_inference_graph.py     --input_type=image_tensor     --pipeline_config_path={pipeline_fname}     --output_directory={output_directory}     --trained_checkpoint_prefix={last_model_path}')


# In[36]:


get_ipython().system('ls {output_directory}')


# ## Download the model `.pb` file

# In[ ]:


import os

pb_fname = os.path.join(os.path.abspath(output_directory), "frozen_inference_graph.pb")
assert os.path.isfile(pb_fname), '`{}` not exist'.format(pb_fname)


# In[ ]:


get_ipython().system('ls -alh {pb_fname}')


# ### Option1 : upload the `.pb` file to your Google Drive
# Then download it from your Google Drive to local file system.
# 
# During this step, you will be prompted to enter the token.

# In[ ]:


# Install the PyDrive wrapper & import libraries.
# This only needs to be done once in a notebook.
get_ipython().system('pip install -U -q PyDrive')
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials


# Authenticate and create the PyDrive client.
# This only needs to be done once in a notebook.
auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

fname = os.path.basename(pb_fname)
# Create & upload a text file.
uploaded = drive.CreateFile({'title': fname})
uploaded.SetContentFile(pb_fname)
uploaded.Upload()
print('Uploaded file with ID {}'.format(uploaded.get('id')))


# ### Option2 :  Download the `.pb` file directly to your local file system
# This method may not be stable when downloading large files like the model `.pb` file. Try **option 1** instead if not working.

# In[ ]:


from google.colab import files
files.download(pb_fname)


# ### OPTIONAL: Download the `label_map.pbtxt` file

# In[ ]:


from google.colab import files
files.download(label_map_pbtxt_fname)


# ### OPTIONAL: Download the modified pipline file
# If you plan to use OpenVINO toolkit to convert the `.pb` file to inference faster on Intel's hardware (CPU/GPU, Movidius, etc.)

# In[ ]:


files.download(pipeline_fname)


# In[ ]:


# !tar cfz fine_tuned_model.tar.gz fine_tuned_model
# from google.colab import files
# files.download('fine_tuned_model.tar.gz')


# In[ ]:





# ## Run inference test
# 
# To test on your own images, you need to upload raw test images to the `test` folder located inside `/data`.
# 
# Right now, this folder contains TFRecord files from Roboflow. We need the raw images.
# 

# #### Add test images to this notebook
# 
# We can download the exact same raw images that are in our Roboflow test split to our local computer by downloading the images in a different (non-TFRecord) format.
# 
# Go back to our [dataset](https://public.roboflow.ai/object-detection/bccd/1), click "Download," select "COCO JSON" as the format, and download to your local machine.
# 
# Unzip the downloaded file, and navigate to the `test` directory.
# ![folder](https://i.imgur.com/xkjxmKP.png)
# 
# 
# Now, on the left-hand side in the colab notebook, select the folder icon.
# ![Colab folder](https://i.imgur.com/59v08qG.png)
# 
# Right-click on `test`, and select "Upload." Navigate to the files locally on your machine you just downloaded...and voila! You're set!
# 

# In[ ]:


# optionally, remove the TFRecord and cells_label_map.pbtxt from
# the test directory so it is only raw images
get_ipython().run_line_magic('cd', '{repo_dir_path}')
get_ipython().run_line_magic('cd', 'data/test')
get_ipython().run_line_magic('rm', 'cells.tfrecord')
get_ipython().run_line_magic('rm', 'cells_label_map.pbtxt')


# In[ ]:


import os
import glob

# Path to frozen detection graph. This is the actual model that is used for the object detection.
PATH_TO_CKPT = pb_fname

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = label_map_pbtxt_fname

# If you want to test the code with your images, just add images files to the PATH_TO_TEST_IMAGES_DIR.
PATH_TO_TEST_IMAGES_DIR =  os.path.join(repo_dir_path, "data/test")

assert os.path.isfile(pb_fname)
assert os.path.isfile(PATH_TO_LABELS)
TEST_IMAGE_PATHS = glob.glob(os.path.join(PATH_TO_TEST_IMAGES_DIR, "*.*"))
assert len(TEST_IMAGE_PATHS) > 0, 'No image found in `{}`.'.format(PATH_TO_TEST_IMAGES_DIR)
print(TEST_IMAGE_PATHS)


# In[ ]:


get_ipython().run_line_magic('cd', '/content/models/research/object_detection')

import numpy as np
import os
import six.moves.urllib as urllib
import sys
import tarfile
import tensorflow as tf
import zipfile

from collections import defaultdict
from io import StringIO
from matplotlib import pyplot as plt
from PIL import Image

# This is needed since the notebook is stored in the object_detection folder.
sys.path.append("..")
from object_detection.utils import ops as utils_ops


# This is needed to display the images.
get_ipython().run_line_magic('matplotlib', 'inline')


from object_detection.utils import label_map_util

from object_detection.utils import visualization_utils as vis_util


# In[ ]:


detection_graph = tf.Graph()
with detection_graph.as_default():
    od_graph_def = tf.GraphDef()
    with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')


label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(
    label_map, max_num_classes=num_classes, use_display_name=True)
category_index = label_map_util.create_category_index(categories)


def load_image_into_numpy_array(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)

# Size, in inches, of the output images.
IMAGE_SIZE = (12, 8)


def run_inference_for_single_image(image, graph):
    with graph.as_default():
        with tf.Session() as sess:
            # Get handles to input and output tensors
            ops = tf.get_default_graph().get_operations()
            all_tensor_names = {
                output.name for op in ops for output in op.outputs}
            tensor_dict = {}
            for key in [
                'num_detections', 'detection_boxes', 'detection_scores',
                'detection_classes', 'detection_masks'
            ]:
                tensor_name = key + ':0'
                if tensor_name in all_tensor_names:
                    tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
                        tensor_name)
            if 'detection_masks' in tensor_dict:
                # The following processing is only for single image
                detection_boxes = tf.squeeze(
                    tensor_dict['detection_boxes'], [0])
                detection_masks = tf.squeeze(
                    tensor_dict['detection_masks'], [0])
                # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
                real_num_detection = tf.cast(
                    tensor_dict['num_detections'][0], tf.int32)
                detection_boxes = tf.slice(detection_boxes, [0, 0], [
                                           real_num_detection, -1])
                detection_masks = tf.slice(detection_masks, [0, 0, 0], [
                                           real_num_detection, -1, -1])
                detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
                    detection_masks, detection_boxes, image.shape[0], image.shape[1])
                detection_masks_reframed = tf.cast(
                    tf.greater(detection_masks_reframed, 0.5), tf.uint8)
                # Follow the convention by adding back the batch dimension
                tensor_dict['detection_masks'] = tf.expand_dims(
                    detection_masks_reframed, 0)
            image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

            # Run inference
            output_dict = sess.run(tensor_dict,
                                   feed_dict={image_tensor: np.expand_dims(image, 0)})

            # all outputs are float32 numpy arrays, so convert types as appropriate
            output_dict['num_detections'] = int(
                output_dict['num_detections'][0])
            output_dict['detection_classes'] = output_dict[
                'detection_classes'][0].astype(np.uint8)
            output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
            output_dict['detection_scores'] = output_dict['detection_scores'][0]
            if 'detection_masks' in output_dict:
                output_dict['detection_masks'] = output_dict['detection_masks'][0]
    return output_dict


# In[ ]:


# Output images not showing? Run this cell again, and try the cell above
# This is needed to display the images.
get_ipython().run_line_magic('matplotlib', 'inline')


# In[ ]:



for image_path in TEST_IMAGE_PATHS:
    image = Image.open(image_path)
    # the array based representation of the image will be used later in order to prepare the
    # result image with boxes and labels on it.
    image_np = load_image_into_numpy_array(image)
    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)
    # Actual detection.
    output_dict = run_inference_for_single_image(image_np, detection_graph)
    # Visualization of the results of a detection.
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_np,
        output_dict['detection_boxes'],
        output_dict['detection_classes'],
        output_dict['detection_scores'],
        category_index,
        instance_masks=output_dict.get('detection_masks'),
        use_normalized_coordinates=True,
        line_thickness=8)
    plt.figure(figsize=IMAGE_SIZE)
    plt.imshow(image_np)

