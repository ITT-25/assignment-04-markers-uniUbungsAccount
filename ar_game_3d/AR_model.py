import pyglet
from pyglet.gl import *
from pyglet.math import Mat4, Vec3
import math


class Model:
    def __init__(self, path, id, win_h, win_w, rot_x=0, rot_y=0, rot_z=0, scaling_factor=1):
        self._id = id
        self._win_h = win_h
        self._win_w = win_w
        self._rot_x = rot_x
        self._rot_y = rot_y
        self._rot_z = rot_z
        self._scaling_factor = scaling_factor

        self._position = None
        self._view_matrix = None
        self._length = None
        self.batch = pyglet.graphics.Batch()
        self._model = pyglet.model.load(path).create_models(batch=self.batch)[0]


    def setup_translation(self, marker_id, view_matrix, position, length):
        if marker_id == self._id:
            self._view_matrix = view_matrix     
            self._position = position
            self._length = length


    def animate(self):
        try:
            # translation matrix to set the position of the 3D model within the window
            trans = Mat4.from_translation(Vec3(
                (self._position[0] - self._win_w/2),
                (self._win_h/2 - self._position[1]), 0))

            # scaling matrix to scale the 3D model appropriatly
            scale = Mat4.from_scale(Vec3(self._scaling_factor, self._scaling_factor, self._scaling_factor))

            # apply view_matrix for rotating the 3D model matching with the rotation of the marker
            # (convert view matrix (numpy array) to Mat4)
            rot = Mat4(
                    self._view_matrix[0, 0], self._view_matrix[0, 1], self._view_matrix[0, 2], 0,
                    self._view_matrix[1, 0], self._view_matrix[1, 1], self._view_matrix[1, 2], 0,
                    self._view_matrix[2, 0], self._view_matrix[2, 1], self._view_matrix[2, 2], 0,
                    0, 0, 0, 1
            )

            # links/recht: x, oben/unten: y, hinten/vorne: z
            rot_x = Mat4.from_rotation(math.radians(self._rot_x), Vec3(1, 0, 0))
            rot_y = Mat4.from_rotation(math.radians(self._rot_y), Vec3(0, 1, 0))
            rot_z = Mat4.from_rotation(math.radians(self._rot_z), Vec3(0, 0, 1))
            
            self._model.matrix = trans @ rot @ rot_x @ rot_z @ rot_y @ scale        
        except:
            pass
        