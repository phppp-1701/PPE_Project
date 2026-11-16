---
annotations_creators: []
language: en
license: cc0-1.0
task_categories:
- object-detection
task_ids: []
pretty_name: hard-hat-detection
tags:
- fiftyone
- image
- object-detection
dataset_summary: '



  ![image/png](dataset_preview.gif)



  This is a [FiftyOne](https://github.com/voxel51/fiftyone) dataset with 5000 samples.


  ## Installation


  If you haven''t already, install FiftyOne:


  ```bash

  pip install -U fiftyone

  ```


  ## Usage


  ```python

  import fiftyone as fo

  import fiftyone.utils.huggingface as fouh


  # Load the dataset

  # Note: other available arguments include ''split'', ''max_samples'', etc

  dataset = fouh.load_from_hub("voxel51/hard-hat-detection")


  # Launch the App

  session = fo.launch_app(dataset)

  ```

  '
---

# Dataset Card for hard-hat-detection

This dataset, contains 5000 images with bounding box annotations in the PASCAL VOC format for these 3 classes:

- Helmet
- Person
- Head




![image/png](dataset_preview.gif)


This is a [FiftyOne](https://github.com/voxel51/fiftyone) dataset with 5000 samples.

## Installation

If you haven't already, install FiftyOne:

```bash
pip install -U fiftyone
```

## Usage

```python
import fiftyone as fo
import fiftyone.utils.huggingface as fouh

# Load the dataset
# Note: other available arguments include 'split', 'max_samples', etc
dataset = fouh.load_from_hub("dgural/hard-hat-detection")

# Launch the App
session = fo.launch_app(dataset)
```


## Dataset Details

### Dataset Description

Improve workplace safety by detecting people and hard hats on 5k images with bbox annotations.


- **Language(s) (NLP):** en
- **License:** cc0-1.0

### Dataset Sources 



- **Repository:** https://www.kaggle.com/datasets/andrewmvd/hard-hat-detection/data



### Source Data

Dataset taken from https://www.kaggle.com/datasets/andrewmvd/hard-hat-detection/data  and created by [andrewmvd](https://www.kaggle.com/andrewmvd)



## Citation 

**BibTeX:**

@misc{make ml,
title={Hard Hat Dataset},
url={https://makeml.app/datasets/hard-hat-workers},
journal={Make ML}}
