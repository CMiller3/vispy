from __future__ import division

from .mesh import MeshVisual
import numpy as np
from numpy.linalg import norm
from ..util.transforms import rotation_matrix


class TubeVisual(MeshVisual):
    """Displays a tube by around a piecewise-linear path.

    The tube mesh is corrected following its Frenet curvature and
    torsion such that it varies smoothly along the curve, including if
    the tube is closed.

    Parameters
    ----------
    points : ndarray
        An array of (x, y, z) points describing the path along which the
        tube will be extruded.
    radius : float
        The radius of the tube. Defaults to 1.0.
    tube_points : int
        The number of points in the approximate circle of the tube's
        cross section. Defaults to 8.
    colors : ndarray | None
        An array of colors at each point of the points array; every
        vertex of the tube mesh around this point will take the given
        color. Must be the same length as the points array, or None
        to color only by the `color` argument. Defaults to None.
    shading : str | None
        Same as for the `MeshVisual` class. Defaults to 'smooth'.
    vertex_colors: ndarray | None
        Same as for the `MeshVisual` class.
    face_colors: ndarray | None
        Same as for the `MeshVisual` class.
    color : Color
        The `Color` to use when drawing the tube. Defaults to (1, 0, 1, 1).
    mode : str
        Same as for the `MeshVisual` class. Defaults to 'triangles'.

    """
    def __init__(self, points, radius=1.0, tube_points=8,
                 colors=None,
                 closed=False,
                 shading='smooth',
                 vertex_colors=None,
                 face_colors=None,
                 color=(1, 0, 1, 1),
                 mode='triangles'):

        points = np.array(points)

        tangents, normals, binormals = _frenet_frames(points, closed)

        segments = len(points) - 1

        # get the positions of each vertex
        grid = np.zeros((len(points), tube_points, 3))
        for i in range(len(points)):
            pos = points[i]
            normal = normals[i]
            binormal = binormals[i]

            # Add a vertex for each point on the circle
            v = np.arange(tube_points, dtype=np.float) / tube_points * 2 * np.pi
            cx = -1. * radius * np.cos(v)
            cy = radius * np.sin(v)
            grid[i] = (pos + cx[:, np.newaxis]*normal +
                       cy[:, np.newaxis]*binormal)

        # construct the mesh
        indices = []
        for i in range(segments):
            for j in range(tube_points):
                ip = (i+1) % segments if closed else i+1
                jp = (j+1) % tube_points

                index_a = i*tube_points + j
                index_b = ip*tube_points + j
                index_c = ip*tube_points + jp
                index_d = i*tube_points + jp

                indices.append([index_a, index_b, index_d])
                indices.append([index_b, index_c, index_d])

        vertices = grid.reshape(grid.shape[0]*grid.shape[1], 3)

        if colors is not None and vertex_colors is None:
            vertex_colors = np.zeros(vertices.shape, dtype=np.float32)
            vertex_colors[:, 0] = np.repeat(colors[:, 0], tube_points)
            vertex_colors[:, 1] = np.repeat(colors[:, 1], tube_points)
            vertex_colors[:, 2] = np.repeat(colors[:, 2], tube_points)

        indices = np.array(indices, dtype=np.uint32)

        MeshVisual.__init__(self, vertices, indices,
                            vertex_colors=vertex_colors,
                            face_colors=face_colors,
                            color=color,
                            shading=shading,
                            mode=mode)
                

    def draw(self, transforms):
        MeshVisual.draw(self, transforms)


def _frenet_frames(points, closed):
    '''Calculates and returns the tangents, normals and binormals for
    the tube.'''
    tangents = np.zeros((len(points), 3))
    normals = np.zeros((len(points), 3))

    epsilon = 0.0001

    # Compute tangent vectors for each segment
    tangents = np.roll(points, -1, axis=0) - np.roll(points, 1, axis=0)
    mags = np.sqrt(np.sum(tangents * tangents, axis=1))
    tangents /= mags[:, np.newaxis]

    # Get initial normal and binormal
    t = np.abs(tangents[0])

    smallest = np.argmin(t)
    normal = np.zeros(3)
    normal[smallest] = 1.

    vec = np.cross(tangents[0], normal)

    normals[0] = np.cross(tangents[0], vec)

    # Compute normal and binormal vectors along the path
    for i in range(1, len(points)):
        normals[i] = normals[i-1]

        vec = np.cross(tangents[i-1], tangents[i])
        if norm(vec) > epsilon:
            vec /= norm(vec)

            theta = np.arccos(np.clip(tangents[i-1].dot(tangents[i]), -1, 1))
            normals[i] = rotation_matrix(vec, theta).dot(normals[i])

    if closed:
        theta = np.arccos(np.clip(normals[0].dot(normals[-1]), -1, 1))
        theta /= len(points) - 1

        if tangents[0].dot(np.cross(normals[0], normals[-1])) > 0:
            theta *= -1.
            
        for i in range(1, len(points)):
            normals[i] = rotation_matrix(tangents[i], theta*i).dot(normals[i])

    binormals = np.cross(tangents, normals)

    return tangents, normals, binormals
