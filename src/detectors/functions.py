import cv2
import numpy as np

from src.non_max_supression.nms import non_max_suppression


def get_contour_detections(mask, thresh=400):
    """ Obtains initial proposed detections from contours discoverd on the mask.
        Scores are taken as the bbox area, larger is higher.
        Inputs:
            mask - thresholded image mask
            thresh - threshold for contour size
        Outputs:
            detectons - array of proposed detection bounding boxes and scores [[x1,y1,x2,y2,s]]
        """
    # get mask contours
    contours, _ = cv2.findContours(mask,
                                   cv2.RETR_EXTERNAL, # cv2.RETR_TREE,
                                   cv2.CHAIN_APPROX_TC89_L1)
    detections = []
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        area = w*h
        if area > thresh: # hyperparameter
            detections.append([x,y,x+w,y+h, area])

    return np.array(detections)


def get_mask(frame1, frame2, kernel=np.array((9, 9), dtype=np.uint8)):
    """ Obtains image mask
        Inputs:
            frame1 - Grayscale frame at time t
            frame2 - Grayscale frame at time t + 1
            kernel - (NxN) array for Morphological Operations
        Outputs:
            mask - Thresholded mask for moving pixels
        """
    frame_diff = cv2.subtract(frame2, frame1)

    # blur the frame difference
    frame_diff = cv2.medianBlur(frame_diff, 3)

    mask = cv2.adaptiveThreshold(
        frame_diff,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        3
    )

    mask = cv2.medianBlur(mask, 3)

    # morphological operations
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    return mask


def get_detections(frame1, frame2, bbox_thresh=400, nms_thresh=1e-3, mask_kernel=np.array((9,9), dtype=np.uint8)):
    """ Main function to get detections via Frame Differencing
        Inputs:
            frame1 - Grayscale frame at time t
            frame2 - Grayscale frame at time t + 1
            bbox_thresh - Minimum threshold area for declaring a bounding box
            nms_thresh - IOU threshold for computing Non-Maximal Supression
            mask_kernel - kernel for morphological operations on motion mask
        Outputs:
            detections - list with bounding box locations of all detections
                bounding boxes are in the form of: (xmin, ymin, xmax, ymax)
        """
    # get image mask for moving pixels
    mask = get_mask(frame1, frame2, mask_kernel)

    # get initially proposed detections from contours
    detections = get_contour_detections(mask, bbox_thresh)

    # separate bboxes and scores
    if len(detections) > 0:
        # perform Non-Maximal Suppression on initial detections
        indices_to_keep = non_max_suppression(detections, iou_threshold=nms_thresh)
        return detections[indices_to_keep]
    return np.zeros((len(detections), 5), dtype=np.float32)


def detections_to_numpy_array(detections: list[tuple]) -> np.array:
    tracks = np.zeros((len(detections), 5), dtype=np.float32)
    for i, detection in enumerate(detections):
        tracks[i][0] = detection[0]
        tracks[i][1] = detection[1]
        tracks[i][2] = detection[2]
        tracks[i][3] = detection[3]
        tracks[i][4] = (detection[2] - detection[0]) * (detection[3] - detection[1])
    return tracks
