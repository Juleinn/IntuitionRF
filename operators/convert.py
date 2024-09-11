import sys
# workaround a bug in vtk/or python interpreter bundled with blender 
from unittest.mock import MagicMock

from ..panels.scene import update_port_list
sys.modules['vtkmodules.vtkRenderingMatplotlib'] = MagicMock()
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import numpy as np
import scipy
import pyopenvdb as vdb
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import convolve, gaussian_filter
import glob
import threading
import time 

def vtr_to_vdb(vtr_file, vdb_file, dicing_factor=8):
    # read input data
    reader = vtk.vtkXMLRectilinearGridReader()
    reader.SetFileName(vtr_file)
    reader.Update()

    output = reader.GetOutput()

    point_data = output.GetPointData()
    a0 = point_data.GetArray(0)
    points = vtk.vtkPoints()
    output.GetPoints(points)

    point_data = vtk_to_numpy(a0)
    point_data_magnitude = np.linalg.norm(point_data, axis=1)
    points = vtk_to_numpy(points.GetData())


    # get irregular grid axes
    points_x = points[:,0]
    points_y = points[:,1]
    points_z = points[:,2]

    # get the offset for the grid
    offset_x = np.min(points_x)
    offset_y = np.min(points_y)
    offset_z = np.min(points_z)

    # get the spacing of the axes
    dx  = np.diff(points_x)
    dy  = np.diff(points_y)
    dz  = np.diff(points_z)

    # non-zero spacing
    dx = dx[dx != 0]
    dy = dy[dy != 0]
    dz = dz[dz != 0]

    # get the smallest cell-dimension in the grid
    minx = np.min(np.abs(dx))
    miny = np.min(np.abs(dy))
    minz = np.min(np.abs(dz))
    cell_size = min(minx, miny, minz)

    # artificially force cell size up to reduce interpolation time
    cell_size *= dicing_factor

    # irregular grid
    grid_dim_x = int((np.max(points_x) - np.min(points_x)) / cell_size)
    grid_dim_y = int((np.max(points_y) - np.min(points_y)) / cell_size)
    grid_dim_z = int((np.max(points_z) - np.min(points_z)) / cell_size)

    grid_x = np.linspace(np.min(points_x), np.max(points_x), grid_dim_x)
    grid_y = np.linspace(np.min(points_y), np.max(points_y), grid_dim_y)
    grid_z = np.linspace(np.min(points_z), np.max(points_z), grid_dim_z)

    # Create an interpolator
    ux = np.unique(points_x)
    uy = np.unique(points_y)
    uz = np.unique(points_z)
    # this is the correct input data
    point_data_magnitude = point_data_magnitude.reshape(len(uz), len(uy), len(ux)).T
    interpolator = RegularGridInterpolator((ux, uy, uz), point_data_magnitude)

    # Generate the regular grid for interpolation
    regular_points = np.array(np.meshgrid(grid_x, grid_y, grid_z, indexing='ij')).T
    regular_points = regular_points.reshape(-1, 3)

    # Interpolation
    interpolated_values = interpolator(regular_points)
    #print('\ninterpolation complete')
    #print(f"{interpolated_values.shape=}")

    # check if there is NaN values in the array

    # Reshape result
    interpolated_volume = interpolated_values.reshape(len(grid_z), len(grid_y), len(grid_x)).T
    
    # log view of the output because of massive scale between min and max values
    do_log = 1
    if do_log:
        interpolated_volume = np.log(interpolated_volume, 
                                    out=np.zeros_like(interpolated_volume), 
                                    where=interpolated_volume!=0)
        # need to add the minimimum to the log'd values because otherwise we get negative attributes
        # from values <1 pre-log
        # need the minimum accross all frames
        min_value = 15
        #print(f"{min_value=}")
        interpolated_volume[interpolated_volume != 0] += min_value
        # remove negative values all together
        interpolated_volume[interpolated_volume < 0] = 0 
        # reduce the total output range
        interpolated_volume *= .01 

    # now we add a peak detection using sobel filtering 
    # filters kernels
    # this largely came from ChatGPT
    sobel_x = np.array([[[1, 0, -1], [2, 0, -2], [1, 0, -1]],
                        [[2, 0, -2], [4, 0, -4], [2, 0, -2]],
                        [[1, 0, -1], [2, 0, -2], [1, 0, -1]]])
    sobel_y = np.array([[[1, 2, 1], [0, 0, 0], [-1, -2, -1]],
                        [[2, 4, 2], [0, 0, 0], [-2, -4, -2]],
                        [[1, 2, 1], [0, 0, 0], [-1, -2, -1]]])
    sobel_z = np.array([[[1, 2, 1], [2, 4, 2], [1, 2, 1]],
                        [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                        [[-1, -2, -1], [-2, -4, -2], [-1, -2, -1]]])

    sobel_x = np.array([
        [[-1,  0,  1], [-3,  0,  3], [-1,  0,  1]],
        [[-3,  0,  3], [-6,  0,  6], [-3,  0,  3]],
        [[-1,  0,  1], [-3,  0,  3], [-1,  0,  1]]
    ])

    sobel_y = np.array([
        [[-1, -3, -1], [ 0,  0,  0], [ 1,  3,  1]],
        [[-3, -6, -3], [ 0,  0,  0], [ 3,  6,  3]],
        [[-1, -3, -1], [ 0,  0,  0], [ 1,  3,  1]]
    ])

    sobel_z = np.array([
        [[-1, -3, -1], [-3, -6, -3], [-1, -3, -1]],
        [[ 0,  0,  0], [ 0,  0,  0], [ 0,  0,  0]],
        [[ 1,  3,  1], [ 3,  6,  3], [ 1,  3,  1]]
    ])


    #interpolated_volume_smoothed = gaussian_filter(interpolated_volume, sigma=10, radius=25)
    interpolated_volume_smoothed = interpolated_volume
    time_start = time.time()
    gradient_x = convolve(interpolated_volume_smoothed, sobel_x, mode='reflect')
    gradient_y = convolve(interpolated_volume_smoothed, sobel_y, mode='reflect')
    gradient_z = convolve(interpolated_volume_smoothed, sobel_z, mode='reflect')
    gradient_x = np.abs(gradient_x)
    gradient_y = np.abs(gradient_y)
    gradient_z = np.abs(gradient_z)

    peaks_x = np.zeros_like(interpolated_volume_smoothed, dtype=bool)
    peaks_y = np.zeros_like(interpolated_volume_smoothed, dtype=bool)
    peaks_z = np.zeros_like(interpolated_volume_smoothed, dtype=bool)

    # remove first element, get positives, remove last element, get negatives
    # were they are both true its a peak
    peaks_x[:-1, :, :] = (gradient_x[:-1, :, :] > 0) & (gradient_x[1:, :, :] < 0)
    peaks_y[:, :-1, :] = (gradient_y[:, :-1, :] > 0) & (gradient_y[:, 1:, :] < 0)
    peaks_z[:, :, :-1] = (gradient_z[:, :, :-1] > 0) & (gradient_z[:, :, 1:] < 0)

    
    # Combine peaks from all directions
    peaks = peaks_x + peaks_y + peaks_z
    peaks = peaks.astype(float)
    peaks_x = peaks_x.astype(float)
    peaks_y = peaks_y.astype(float)
    peaks_z = peaks_z.astype(float)
    peaks = gaussian_filter(peaks, sigma=2, radius=2)

    ### --------------------
    ### VDB stuff now
    ### --------------------

    vdb_grid = vdb.FloatGrid()
    #vdb_grid.background = 0.0
    vdb_grid.name = 'magnitude'

    sobel_grid = vdb.FloatGrid()
    sobel_grid.name = 'sobel'

    sobel_grid_x = vdb.FloatGrid()
    sobel_grid_x.name = 'sobel_x'
    sobel_grid_y = vdb.FloatGrid()
    sobel_grid_y.name = 'sobel_y'
    sobel_grid_z = vdb.FloatGrid()
    sobel_grid_z.name = 'sobel_z'

    accessor = vdb_grid.getAccessor()
    sobel_accessor = sobel_grid.getAccessor()
    sobel_accessor_x = sobel_grid_x.getAccessor()
    sobel_accessor_y = sobel_grid_y.getAccessor()
    sobel_accessor_z = sobel_grid_z.getAccessor()

    # compute the scale factor 
    scale_factor = 1 / cell_size
    print(f"scale_factor = {scale_factor} ( scale down by a factor of {cell_size})")

    for index_x, x in enumerate(grid_x):
        for index_y, y in enumerate(grid_y):
            for index_z, z in enumerate(grid_z):
                accessor.setValueOn((index_x, index_y, index_z),
                                    interpolated_volume[index_x][index_y][index_z])
                sobel_accessor.setValueOn((index_x, index_y, index_z),
                                    gradient_x[index_x][index_y][index_z] +
                                    gradient_y[index_x][index_y][index_z] + 
                                    gradient_z[index_x][index_y][index_z])
                sobel_accessor_x.setValueOn((index_x, index_y, index_z),
                                    gradient_x[index_x][index_y][index_z])
                sobel_accessor_y.setValueOn((index_x, index_y, index_z),
                                    gradient_y[index_x][index_y][index_z])
                sobel_accessor_z.setValueOn((index_x, index_y, index_z),
                                    gradient_z[index_x][index_y][index_z])


    #print(f"write {vdb_file}")
    vdb.write(vdb_file, grids=[vdb_grid, sobel_grid, sobel_grid_x, sobel_grid_y, sobel_grid_z])

    return scale_factor, (offset_x, offset_y, offset_z)
