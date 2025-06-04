import cv2
import numpy as np
import pyglet
from PIL import Image
from pathlib import Path

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

TARGET_CORNERS = np.array(
    [[0, 0],
     [SCREEN_WIDTH - 1, 0],
     [SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1],
     [0, SCREEN_HEIGHT - 1]], dtype="float32"
)

def loadImg(image_path: Path):
    picture = pyglet.image.load(str(image_path))
    picture.anchor_x = picture.width // 2
    picture.anchor_y = picture.height // 2
    spriteObject = pyglet.sprite.Sprite(picture)
    return spriteObject


def convertCvFrameToPyglet(frame_bgr):
    if frame_bgr is None:
        return None
    heightPixels = frame_bgr.shape[0]
    widthPixels = frame_bgr.shape[1]
    rawBytes = Image.fromarray(frame_bgr).tobytes()
    return pyglet.image.ImageData(
        widthPixels,
        heightPixels,
        "BGR",
        rawBytes,
        pitch=-widthPixels * 3
    )


def warpCameraImageToWholeScreen(source_bgr, source_points):
    matrix = cv2.getPerspectiveTransform(
        np.array(source_points, dtype=np.float32),
        TARGET_CORNERS
    )
    warpedImage = cv2.warpPerspective(
        source_bgr,
        matrix,
        (SCREEN_WIDTH, SCREEN_HEIGHT)
    )
    return warpedImage

def findHighestVisibleFingertipCandidate(image_bgr):
    grayFrame = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    if not hasattr(findHighestVisibleFingertipCandidate, "backgroundModel"):
        findHighestVisibleFingertipCandidate.backgroundModel = grayFrame.copy().astype("float")
        return None

    cv2.accumulateWeighted(grayFrame, findHighestVisibleFingertipCandidate.backgroundModel, 0.4)

    background8u = cv2.convertScaleAbs(findHighestVisibleFingertipCandidate.backgroundModel)
    movementMask = cv2.absdiff(grayFrame, background8u)

    _, movementMask = cv2.threshold(movementMask, 25, 255, cv2.THRESH_BINARY)
    movementMask = cv2.dilate(movementMask, None, iterations=2)

    contours, _ = cv2.findContours(movementMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        return None

    biggestContour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggestContour) < 500: #return none if no thicc enough fingertip detected
        return None

    highestPointIndex = biggestContour[:, :, 1].argmin()
    x, y = biggestContour[highestPointIndex][0]
    return (int(x), int(y))
