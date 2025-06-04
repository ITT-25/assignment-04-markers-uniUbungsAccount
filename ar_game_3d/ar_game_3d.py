from __future__ import annotations

import time
import math
from typing import List, Dict, Tuple

import cv2
import cv2.aruco as aruco
import numpy as np
from PIL import Image
import pyglet
from pyglet.gl import *
from pyglet.math import Mat4, Vec3

from AR_model import Model

if not hasattr(Model, "id"):
    Model.id = property(lambda self: getattr(self, "_id", None))

INVERSE_MATRIX = np.array(
    [
        [1.0, 1.0, 1.0, 1.0],
        [-1.0, -1.0, -1.0, -1.0],
        [-1.0, -1.0, -1.0, -1.0],
        [1.0, 1.0, 1.0, 1.0],
    ],
    dtype=float,
)

LASER_LEN = 230
LASER_TTL = 0.3
HIT_TTL = 0.3
LASER_COLOR = (0, 255, 0)
HIT_COLOR = (0, 0, 255)

lasers: List[Dict[str, object]] = []

## to convert color space of opencv to color space of pyglet
## https://gist.github.com/nkymut/1cb40ea6ae4de0cf9ded7332f1ca0d55
def cv2glet(img,fmt):
    '''Assumes image is in BGR color space. Returns a pyimg object'''
    if fmt == 'GRAY':
      rows, cols = img.shape
      channels = 1
    else:
      rows, cols, channels = img.shape

    raw_img = Image.fromarray(img).tobytes()

    top_to_bottom_flag = -1
    bytes_per_row = channels*cols
    pyimg = pyglet.image.ImageData(width=cols, 
                                   height=rows, 
                                   fmt=fmt, 
                                   data=raw_img, 
                                   pitch=top_to_bottom_flag*bytes_per_row)
    return pyimg


## estimates the position of a marker within the camera coordinate system
## returns rotation and translation vectors of marker in camera coordinate system
def estimatePoseMarker(corners, mtx, distortion):
    global length
    length = abs(corners[0][0][0] - corners[0][1][0]) if (abs(corners[0][0][0] - corners[0][1][0]) > abs(corners[0][0][0] - corners[0][2][0])) else abs(corners[0][0][0] - corners[0][2][0])
    marker_points = np.array([[-length / 2, length / 2, 0],
                              [length / 2, length / 2, 0],
                              [length / 2, -length / 2, 0],
                              [-length / 2, -length / 2, 0]], dtype=np.float32)
    rvecs = []
    tvecs = []
    for c in corners:
        _, r, t = cv2.solvePnP(marker_points, c, mtx, distortion, False, cv2.SOLVEPNP_IPPE_SQUARE)
        rvecs.append(r)
        tvecs.append(t)
    return np.array([rvecs]), np.array([tvecs])

def get_center_of_marker(corners):
    center_x = corners[0][0] - ((corners[0][0] - corners[2][0])/2)
    center_y = corners[0][1] - ((corners[0][1] - corners[2][1])/2)
    return (center_x, center_y)

def point_line_distance(pt: Tuple[int, int], a: Tuple[int, int], b: Tuple[int, int]) -> float:
    px, py = pt
    ax, ay = a
    bx, by = b
    if (ax, ay) == (bx, by):
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / (
        (bx - ax) ** 2 + (by - ay) ** 2
    )
    t = max(0.0, min(1.0, t))
    closest_x = ax + t * (bx - ax)
    closest_y = ay + t * (by - ay)
    return math.hypot(px - closest_x, py - closest_y)

win_w = 640
win_h = 480
cam_z = 420

window = pyglet.window.Window(win_w, win_h, resizable=False)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("keine webcam gefunden!")

camera_mtx = np.array(
    [
        [534.34144579, 0.0, 339.15527836],
        [0.0, 534.68425882, 233.84359494],
        [0.0, 0.0, 1.0],
    ],
    dtype=np.float64,
)
dist_coeffs = np.zeros((4, 1))

aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
aruco_params = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, aruco_params)

models: List[Model] = [
    #  Model("enton.obj", 0, win_h, win_w, 270, 90, 270, 0.2), can work with Marker-Sheet 0-3 ID
    Model("enton.obj", 4, win_h, win_w, 270, 90, 270, 0.2),
    Model("enton.obj", 5, win_h, win_w, 270, 90, 270, 0.2),
]

for m in models:
    m._last_seen = 0.0
    m._hit_until = 0.0
    m._yaw = 0.0

@window.event
def on_draw():
    ok, frame = cap.read()
    if not ok:
        return

    now = time.time()

    grayFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners_list, ids, _ = detector.detectMarkers(grayFrame)
    aruco.drawDetectedMarkers(frame, corners_list)

    if ids is not None:
        for idx, id_arr in enumerate(ids):
            m_id = int(id_arr[0])
            corners = corners_list[idx]

            rvecs, tvecs = estimatePoseMarker(corners, camera_mtx, dist_coeffs)
            rvec = rvecs[0][0]
            tvec = tvecs[0][0]

            rot_mat, _ = cv2.Rodrigues(rvec)
            yaw = math.atan2(rot_mat[1, 0], rot_mat[0, 0])

            tx, ty, tz = map(float, tvec.flatten())
            view_mat = INVERSE_MATRIX * np.array(
                [
                    [rot_mat[0][0], rot_mat[0][1], rot_mat[0][2], tx],
                    [rot_mat[1][0], rot_mat[1][1], rot_mat[1][2], ty],
                    [rot_mat[2][0], rot_mat[2][1], rot_mat[2][2], tz],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=float,
            )
            view_mat = view_mat.T.astype(np.float32)

            cx, cy = map(int, get_center_of_marker(corners[0]))

            for mdl in models:
                if mdl._id == m_id:
                    mdl._view_matrix = view_mat
                    mdl._position = (cx, cy)
                    mdl._length = length
                    mdl._last_seen = now
                    mdl._yaw = yaw

    for mdl in models:
        if now - mdl._last_seen > 0.5:
            mdl._view_matrix = None

    for mdl in models:
        if mdl._view_matrix is None or mdl._position is None:
            continue
        sx, sy = mdl._position
        ex = int(sx + LASER_LEN * math.cos(mdl._yaw))
        ey = int(sy + LASER_LEN * math.sin(mdl._yaw))
        lasers.append(
            {"start": (sx, sy), "end": (ex, ey), "expires": now + LASER_TTL, "owner_id": mdl._id}
        )

    lasers[:] = [l for l in lasers if l["expires"] > now]

    for laser in lasers:
        for target in models:
            if target._id == laser["owner_id"]:
                continue
            if target._view_matrix is None or target._position is None:
                continue
            if point_line_distance(target._position, laser["start"], laser["end"]) < 20:
                target._hit_until = now + HIT_TTL

    for laser in lasers:
        cv2.line(frame, laser["start"], laser["end"], LASER_COLOR, 2)

    for mdl in models:
        if mdl._position and now < mdl._hit_until:
            cv2.circle(frame, mdl._position, 25, HIT_COLOR, -1)

    pyg_img = cv2glet(frame, "BGR")
    window.clear()
    pyg_img.blit(-win_w / 2, -win_h / 2, 0)

    for mdl in models:
        if mdl._view_matrix is not None:
            mdl.batch.draw()

@window.event
def on_resize(w: int, h: int):
    window.viewport = (0, 0, w, h)
    window.projection = Mat4.perspective_projection(window.aspect_ratio, 0.1, 1024)
    return pyglet.event.EVENT_HANDLED

def animate(dt: float):
    for mdl in models:
        mdl.animate()

if __name__ == "__main__":
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)

    window.view = Mat4.look_at(Vec3(0, 0, cam_z), Vec3(0, 0, 0), Vec3(0, 1, 0))
    window.viewport = (0, 0, win_w, win_h)
    window.projection = Mat4.perspective_projection(window.aspect_ratio, 0.1, 1024)



    pyglet.clock.schedule_interval(animate, 1 / 60.0)
    pyglet.app.run()
