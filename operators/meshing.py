import bpy 
import sys
import bmesh
import mathutils
from mathutils import geometry
import os
import numpy as np 
import matplotlib.pyplot as plt
import math
import glob
from collections import defaultdict
from . import convert
from .convert import run_parrallel
import multiprocessing

# workaround a bug in vtk/or python interpreter bundled with blender 
from unittest.mock import MagicMock

from ..panels.scene import update_port_list
sys.modules['vtkmodules.vtkRenderingMatplotlib'] = MagicMock()
import vtk

from CSXCAD import CSXCAD, CSPrimitives
from openEMS import openEMS
from openEMS.physical_constants import *

# workaround for blender not letting me register a LumpedPort to 
# a blender object (probably for serialization ?)
# Its OK to loose thoose references on blender exit (for now)
from collections import defaultdict
ports = defaultdict(lambda: None)
nf2ff = None

import tempfile

def extract_lines_xyz(lines):
    mesh = lines.data
    verts = mesh.vertices
    edges = mesh.edges
    
    x = set()
    y = set()
    z = set()
    
    for edge in edges:
        if verts[edge.vertices[0]].co[0] != verts[edge.vertices[1]].co[0]:
            x.add(verts[edge.vertices[0]].co[0])
            x.add(verts[edge.vertices[1]].co[0])            
        if verts[edge.vertices[0]].co[1] != verts[edge.vertices[1]].co[1]:
            y.add(verts[edge.vertices[0]].co[1])
            y.add(verts[edge.vertices[1]].co[1])            
        if verts[edge.vertices[0]].co[2] != verts[edge.vertices[1]].co[2]:
            z.add(verts[edge.vertices[0]].co[2])
            z.add(verts[edge.vertices[1]].co[2])            
        
    return (x, y, z)

def add_meshline(context, direction):
    bpy.ops.object.mode_set(mode='OBJECT')
    # backup which object we're currently editing
    source_object = context.view_layer.objects.active
    
    # backup source selected vertices to slice at
    source_selected_verts = [v for v in bpy.context.active_object.data.vertices if v.select]
    
    bm = bmesh.new()
    bm.from_mesh(context.scene.intuitionRF_lines.data)
    
    # switch to the lines object
    for vert in source_selected_verts:
        for edge in bm.edges:            
            # compute intersection points between face (selected vert, normal +x) 
            # and every edge in meshing the lines
            v1, v2 = edge.verts
            intersection = geometry.intersect_line_plane(v1.co, v2.co, vert.co, direction)
            if intersection is not None:
                # exclude out of bounds hit
                if (v2.co - v1.co).length_squared > (intersection - v1.co).length_squared and \
                    (v2.co - v1.co).length_squared > (intersection - v2.co).length_squared:
                    # add intersection as new vertex
                    new_vertex = bm.verts.new(intersection)
                    bm.verts.index_update()
                    
                    new_edge_1 = bm.edges.new((v1, new_vertex))
                    new_edge_2 = bm.edges.new((new_vertex, v2))
                    # add 2 edges from v1 to intersection and v2 to intersection
                    
                    # delete old existing edge
                    bmesh.ops.delete(bm, geom=[edge], context='EDGES')
    
    bm.verts.index_update()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.000001)
    
    bm.to_mesh(context.scene.intuitionRF_lines.data)
    bm.free()
    # switch back to the source object    
    source_object = context.view_layer.objects.active
    # switch back to edit mode
    bpy.ops.object.mode_set(mode='EDIT')

class IntuitionRF_OT_add_meshline_x(bpy.types.Operator):
    """ IntuitionRF : edit mode operator, gets the selected vertices, and slices the 
    mesh lines at the x projection of vertex to add line at the given position """
    bl_idname = "intuitionrf.add_meshline_x"
    bl_label = "Add meshline x"
    
    def execute(self, context):
        vec_x = mathutils.Vector((1.0, 0.0, 0.0))
        add_meshline(context, vec_x)
        
        return {"FINISHED"}
    
class IntuitionRF_OT_add_meshline_y(bpy.types.Operator):
    """ IntuitionRF : edit mode operator, gets the selected vertices, and slices the 
    mesh lines at the y projection of vertex to add line at the given position """
    bl_idname = "intuitionrf.add_meshline_y"
    bl_label = "Add meshline y"
    
    def execute(self, context):
        vec_y = mathutils.Vector((0.0, 1.0, 0.0))
        add_meshline(context, vec_y)
        
        return {"FINISHED"}
    
class IntuitionRF_OT_add_meshline_z(bpy.types.Operator):
    """ IntuitionRF : edit mode operator, gets the selected vertices, and slices the 
    mesh lines at the z projection of vertex to add line at the given position """
    bl_idname = "intuitionrf.add_meshline_z"
    bl_label = "Add meshline z"
    
    def execute(self, context):
        vec_z = mathutils.Vector((0.0, 0.0, 1.0))
        add_meshline(context, vec_z)
        
        return {"FINISHED"}

class IntuitionRF_OT_add_domain(bpy.types.Operator):
    """ Add a IntuitionRF simulation domain """
    bl_idname = "intuitionrf.add_domain"
    bl_label = "Add a \u03BB/2 RF simulation domain"
    
    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add()
        cube = context.active_object
        cube.name = "IntuitionRF_domain"
        bpy.context.view_layer.objects.active = cube
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        # lambda = c/f ~= 300/MHz
        wavelength_over_2 = .5 * 300 / context.scene.center_freq
        # default cube is twice as big as the unit cube
        bpy.ops.transform.resize(value=(.5 * wavelength_over_2,.5 * wavelength_over_2,.5 * wavelength_over_2))
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        cube.display_type = 'WIRE'
        cube.show_name = True
        context.scene.intuitionRF_domain = cube
        self.report({'INFO'}, "Custom function executed!")
        return {"FINISHED"}
    
class IntuitionRF_OT_add_wavelength_cube(bpy.types.Operator):
    """ Add a IntuitionRF simulation domain """
    bl_idname = "intuitionrf.add_wavelength_cube"
    bl_label = "Add a \u03BB/20 reference cube"
    
    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add()
        cube = context.active_object
        cube.name = "wavelength_over_20"
        bpy.context.view_layer.objects.active = cube
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        # lambda = c/f ~= 300/MHz
        wavelength_over_20 = (300 / context.scene.center_freq) / 20
        # default cube is twice as big as the unit cube
        bpy.ops.transform.resize(value=(.5 * wavelength_over_20,.5 * wavelength_over_20,.5 * wavelength_over_20))
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        cube.display_type = 'WIRE'
        cube.show_name = True
        context.scene.intuitionRF_domain = cube
        return {"FINISHED"}
    
class IntuitionRF_OT_add_default_lines(bpy.types.Operator):
    """ Add a IntuitionRF default meshing lines set """
    bl_idname = "intuitionrf.add_default_lines"
    bl_label = "Add a default meshing line set of \u03BB/2"
    
    def execute(self, context):
        mesh = bpy.data.meshes.new("mesh")  # add a new mesh
        lines = bpy.data.objects.new("lines", mesh)  # add a new object using the mesh
        bpy.context.collection.objects.link(lines)
        bpy.context.view_layer.objects.active = lines
        
        wavelength_over_2 = 300 / bpy.context.scene.center_freq
        
        verts = [(-wavelength_over_2 / 2, -wavelength_over_2 / 2, -wavelength_over_2 / 2),
        (wavelength_over_2 / 2, -wavelength_over_2 / 2, -wavelength_over_2 / 2),
        (-wavelength_over_2 / 2, wavelength_over_2 / 2, -wavelength_over_2 / 2),
        (-wavelength_over_2 / 2, -wavelength_over_2 / 2, wavelength_over_2 / 2),
        ]
        edges = [[0, 1], [0, 1], [0, 2], [0, 3]]
        faces = []
        mesh.from_pydata(verts, edges, faces)
        lines.show_name = True

        context.scene.intuitionRF_lines = lines
        # lets set the default smoothing max res to lambda/40
        context.scene.intuitionRF_smooth_max_res = wavelength_over_2 / 20
        return {"FINISHED"}
    
class IntuitionRF_OT_preview_CSX(bpy.types.Operator):
    """Preview SIM from current configuration in CSXCAD"""
    bl_idname = "intuitionrf.preview_csx"
    bl_label = "Preview sim in CSXCAD"

    def execute(self, context):
        FDTD = openEMS(NrTS=1, EndCriteria=1e-4)


        CSX = CSXCAD.ContinuousStructure()
        CSX = meshlines_from_scene(CSX, context)
        FDTD.SetCSX(CSX)
        FDTD.SetGaussExcite( context.scene.center_freq * 1e6, context.scene.cutoff_freq * 1e6)
        FDTD.SetBoundaryCond( ['MUR', 'MUR', 'MUR', 'MUR', 'MUR', 'PML_8'] )

        FDTD, CSX = objects_from_scene(FDTD, CSX, context)

        mesh = CSX.GetGrid()
        mesh_res = context.scene.intuitionRF_smooth_max_res
        mesh.SmoothMeshLines('all', mesh_res, 1.4)

        # create temporary dir
        tmp_dir = tempfile.mkdtemp()
        CSX_file = f"{tmp_dir}/meshing.xml"
        CSX.Write2XML(CSX_file)

        from CSXCAD import AppCSXCAD_BIN
        os.system(AppCSXCAD_BIN + ' "{}"'.format(CSX_file))

        return {"FINISHED"}

class IntuitionRF_OT_preview_PEC_dump(bpy.types.Operator):
    """Preview SIM from current configuration in CSXCAD"""
    bl_idname = "intuitionrf.preview_pec_dump"
    bl_label = "View PEC dump"

    def execute(self, context):
        FDTD = openEMS(NrTS=1, EndCriteria=1e-4)

        CSX = CSXCAD.ContinuousStructure()
        CSX = meshlines_from_scene(CSX, context)
        FDTD.SetCSX(CSX)
        FDTD.SetGaussExcite( context.scene.center_freq * 1e6, context.scene.cutoff_freq * 1e6)
        FDTD.SetBoundaryCond( ['MUR', 'MUR', 'MUR', 'MUR', 'MUR', 'PML_8'] )

        FDTD, CSX = objects_from_scene(FDTD, CSX, context)

        #mesh = CSX.GetGrid()
        #mesh_res = context.scene.intuitionRF_smooth_max_res
        #mesh.SmoothMeshLines('all', mesh_res, 1.4)

        # dry run the SIM
        FDTD.Run(sim_path=context.scene.intuitionRF_simdir, cleanup=False, setup_only=True, debug_material=True, debug_pec=True)

        # now import the meshing lines from the output VTP file
        PEC_filename = f"{context.scene.intuitionRF_simdir}/PEC_dump.vtp"
        PEC_dump_to_scene(PEC_filename, context)

        return {"FINISHED"}

class IntuitionRF_OT_run_sim(bpy.types.Operator):
    """Run the currently defined simulation in OpenEMS"""
    bl_idname = "intuitionrf.run_sim"
    bl_label = "Run SIM"

    def execute(self, context):
        run_sim(context)
        return {"FINISHED"}

def run_sim(context):
    global nf2ff
    FDTD = openEMS(NrTS=1e6, EndCriteria=1e-4)
    if context.scene.intuitionRF_oversampling > 1:
        FDTD.SetOverSampling(context.scene.intuitionRF_oversampling)

    CSX = CSXCAD.ContinuousStructure()
    CSX = meshlines_from_scene(CSX, context)
    FDTD.SetCSX(CSX)
    if context.scene.intuitionRF_excitation_type == "gauss":
        FDTD.SetGaussExcite( context.scene.center_freq * 1e6, context.scene.cutoff_freq * 1e6)
    elif context.scene.intuitionRF_excitation_type == "custom":
        FDTD.SetCustomExcite( context.scene.intuitionRF_excitation_custom_function, context.scene.center_freq * 1e6, context.scene.cutoff_freq * 1e6)
    else:
        FDTD.SetSinusExcite( context.scene.center_freq * 1e6)

    FDTD.SetBoundaryCond( ['MUR', 'MUR', 'MUR', 'MUR', 'MUR', 'MUR'] )

    FDTD, CSX = objects_from_scene(FDTD, CSX, context)

    mesh = CSX.GetGrid()
    mesh_res = context.scene.intuitionRF_smooth_max_res
    mesh.SmoothMeshLines('all', mesh_res, 1.4)

    # Add the nf2ff recording box
    nf2ff = FDTD.CreateNF2FFBox()

    FDTD.Run(sim_path=context.scene.intuitionRF_simdir, cleanup=False)

    update_port_list(ports)

    return (FDTD, CSX, nf2ff, ports)

class IntuitionRF_OT_compute_NF2FF(bpy.types.Operator):
    """Compute the near field to far field at resonnant frequency"""
    bl_idname = "intuitionrf.compute_nf2ff"
    bl_label = "Compute NF2FF"

    def execute(self, context):
        global nf2ff
        if nf2ff == None:
            self.report({'INFO'}, "NF2FF does not exist. (re)run sim")
            return {"FINISHED"}


        self.report({'INFO'}, "Computing NF2FF. This may take some time")
        step_degrees = 5.0
        step_count_theta = int(180 / step_degrees) 
        step_count_phi = int(360 / step_degrees) 
        theta = np.arange(-180.0, 180.0, step_degrees)
        phi = np.arange(-360.0, 360.0, step_degrees)
        nf2ff_res = nf2ff.CalcNF2FF(
            sim_path=context.scene.intuitionRF_simdir,
            freq=context.scene.intuitionRF_resonnant_freq * 1e6,
            theta=theta,
            phi=phi,
            center=[0,0,0]
        )

        # phi = 0 => x-z plane
        # theta = 90 => x-y plane
        # phi 'horizontal' starting at X axis
        # theta 'vertical' starting at Z axis

        Dmax_dB = 10*np.log10(nf2ff_res.Dmax[0])
        # don't know why add directivity but seems to be the way
        # E_norm[0] -> frequency index 0 (only on here)
        E_norm = 20.0*np.log10(nf2ff_res.E_norm[0]/np.max(nf2ff_res.E_norm[0])) \
            + 10*np.log10(nf2ff_res.Dmax[0])

        E_min = np.min(E_norm)

        # E_norm[theta][phi]
        #
        # create a new mesh
        mesh = bpy.data.meshes.new("rad_pattern")  # add a new mesh
        rad_pat = bpy.data.objects.new(f"radiation_pattern_peak_{nf2ff_res.Dmax[0]:.2f}_dBi", mesh)  # add a new object using the mesh
        bpy.context.collection.objects.link(rad_pat)
        
        # draw lines in each directions         
        verts = []
        edges = []
        faces = []
        for it, t in enumerate(theta * math.pi / 180):
            for ip, p in enumerate(phi * math.pi / 180):
                # can probably do this numpy-way but we need the indices for meshing

                # need to offset such that there is no negative gain furthur out than pos
                norm = E_norm[it][ip] - E_min
                # norm = 1
                x = math.sin(t) * math.cos(p) * norm
                y = math.sin(t) * math.sin(p) * norm
                z = math.cos(t) * norm

                # scaling factor here ?

                verts.append(tuple((x, y, z)))

        for it, _ in enumerate(theta[:-1]):
            for ip, _ in enumerate(phi[:-1]):
                i0 = (it * step_count_phi) + ip
                i1 = (it * step_count_phi) + ip + 1
                i2 = ((it+1) * step_count_phi) + ip 
                i3 = ((it+1) * step_count_phi) + ip + 1

                faces.append([i0, i1, i3, i2])

        mesh.from_pydata(verts, edges, faces)
        mesh.validate(verbose=True)

                # do a uv-sphere meshing here

        self.report({'INFO'}, "Complete")
        
        return {"FINISHED"}

class IntuitionRF_OT_check_updates(bpy.types.Operator):
    """Check for plugin updates"""
    bl_idname = "intuitionrf.check_updates"
    bl_label = "Check Plugin Updates"

    def execute(self, context):
        current_version = sys.modules.get('IntuitionRF').bl_info['version']

        import requests
        import json
        r = requests.get("https://api.github.com/repos/Juleinn/IntuitionRF/releases/latest")

        if r.status_code != 200:
            self.report({'ERROR'}, "Failed to get latest version number. Please check manually")
            return {"FINISHED"}

        latest_tagname = json.loads(r.content)['tag_name']

        latest_major = int(latest_tagname[0])
        latest_minor = int(latest_tagname[2])
        latest_patch = int(latest_tagname[4])
        
        if latest_major == current_version[0] and latest_minor == current_version[1] and latest_patch == current_version[2]:
            self.report({'INFO'}, "IntuitionRF is up to date")
        else: 
            self.report({'INFO'}, f"Current {current_version[0]}.{current_version[1]}.{current_version[2]} - Latest: {latest_tagname[:5]} ({latest_tagname})")

        return {"FINISHED"}

class IntuitionRF_impedance_plotter(bpy.types.Operator):
    """Base class for operators for plotting from the object context 
    aswell as from the scene panel"""
    def plot_impedance(self, port, context):
        f0 = context.scene.center_freq * 1e6 
        fc = context.scene.cutoff_freq * 1e6
        f = np.linspace(f0-fc,f0+fc,601)

        try:
            port.CalcPort(context.scene.intuitionRF_simdir, f)
        except:
            self.report({'INFO'}, "Failed to calc port")

        Zin = port.uf_tot / port.if_tot

        plt.plot(f/1e6, np.real(Zin), 'k-', label='$\Re\{Z_{in}\}$')
        plt.plot(f/1e6, np.imag(Zin), 'r--', label='$\Im\{Z_{in}\}$')
        plt.plot(f/1e6, np.absolute(Zin), label='Mag')
        plt.legend()
        plt.title('Port impedance')
        plt.ylabel('Impedance (ohm)')
        plt.xlabel('Frequency (MHz)')
        plt.grid()
        plt.show()


class IntuitionRF_OT_plot_port_impedance(IntuitionRF_impedance_plotter):
    """Run the currently defined simulation in OpenEMS"""
    bl_idname = "intuitionrf.plot_port_impedance"
    bl_label = "Plot Impedance"

    def execute(self, context):
        active_port = bpy.context.view_layer.objects.active 
        if not active_port.intuitionRF_properties.object_type == "port":
            self.report({'INFO'}, "Cannot plot impedance : not a port")

        port = ports[active_port.name]
        
        self.plot_impedance(port, context)

        return {"FINISHED"}

class IntuitionRF_OT_plot_impedance(IntuitionRF_impedance_plotter):
    """Run the currently defined simulation in OpenEMS"""
    bl_idname = "intuitionrf.plot_impedance"
    bl_label = "Plot Impedance"

    def execute(self, context):
        active_port = ports[context.scene.intuitionRF_port_selector]

        self.plot_impedance(active_port, context)


        return {"FINISHED"}


def calc_port(port, context):
    f0 = context.scene.center_freq * 1e6 
    fc = context.scene.cutoff_freq * 1e6
    f = np.linspace(f0-fc,f0+fc,601)
    port.CalcPort(context.scene.intuitionRF_simdir, f)

    Zin = port.uf_tot / port.if_tot
    s11 = port.uf_ref/port.uf_inc
    s11_dB = 20.0*np.log10(np.abs(s11))
    return f, s11_dB

class IntuitionRF_returnloss_plotter(bpy.types.Operator):
    """Baseclass for running the s11 plots from the object 
    and scene panels contexts"""

    def plot_s11(self, port, context):
        try:
            f, s11_dB = calc_port(port, context)
            plt.plot(f/1e6, s11_dB)
            plt.ylabel('s11 (dB)')
            plt.xlabel('f (MHz)')
            plt.grid()
            plt.show()

            # put resonnant frequency to the scene res. freq 
            # multiple port not handled yet
            res_freq = f[np.argmin(s11_dB)] / 1e6
            context.scene.intuitionRF_resonnant_freq = res_freq
        except:
            self.report({'INFO'}, "Failed to calc port")

class IntuitionRF_OT_convert_volume_single_frame(bpy.types.Operator):
    """Convert the current frame's vtk dump for selected dump object 
    to OpenVDB file (if frame in available files range, ordered by name)"""
    bl_idname = "intuitionrf.convert_volume_single_frame"
    bl_label = "Convert Current Frame"

    def execute(self, context):
        # find all vtk files in simdir for current dump box (could be 0 if sim never ran)
        simdir = context.scene.intuitionRF_simdir
        object_name = context.active_object.name

        files = sorted(glob.glob(f"{os.path.join(simdir, object_name)}*vtr"))
        frame_relative = context.scene.frame_current - context.scene.frame_start
        if frame_relative >= len(files):
            self.report({"ERROR"}, "Current frame is out of existing computed dump files bounds")
            return {"FINISHED"}

        # find the appropriate file 
        file_vtr = files[frame_relative]
        file_vdb = file_vtr.replace(".vtr", ".vdb") # this will cause bug if the object has .vtr as part of name 
        self.report({"INFO"}, f"Computing OpenVDB for file {file_vtr}")

        dicing_factor = context.active_object.intuitionRF_properties.dicing_factor
        
        scale_factor, offset = convert.vtr_to_vdb(file_vtr, file_vdb, dicing_factor)

        # scaling here doesnt seem to work
        bpy.ops.object.volume_import(
            filepath=file_vdb, 
            directory=os.path.dirname(file_vdb), 
            files=[{"name":os.path.basename(file_vdb)}], 
            relative_path=True, 
            align='WORLD', 
            location=(0, 0, 0), 
            scale=(1,1,1)
        )

        bpy.ops.transform.resize(value=(1/scale_factor, 1/scale_factor, 1/scale_factor))
        bpy.ops.transform.translate(value=offset)

        return {"FINISHED"}


class IntuitionRF_OT_convert_volume_all_frames(bpy.types.Operator):
    """Convert all frames' vtk dump for selected dump object 
    to OpenVDB files (for all frames available in file range, ordered by name)"""
    bl_idname = "intuitionrf.convert_volume_all_frames"
    bl_label = "Convert all Frames"

    def execute(self, context):
        simdir = context.scene.intuitionRF_simdir
        object_name = context.active_object.name
        thread_count = context.active_object.intuitionRF_properties.thread_count

        files = sorted(glob.glob(f"{os.path.join(simdir, object_name)}*vtr"))
        files_splits = np.array_split(np.array(list(enumerate(files))), thread_count)

        dicing_factor = context.active_object.intuitionRF_properties.dicing_factor

        args = list(zip(files_splits, [object_name] * len(files_splits), [dicing_factor] * len(files_splits)))

        results = run_parrallel(args, thread_count)

        scale_factor, offset = results[0] # should all be the same
        print(scale_factor)
        print(offset)

        files = sorted(glob.glob(f"{os.path.join(simdir, object_name)}*vdb"))
        files_vdb = []
        for file in files:
            file_vdb = os.path.basename(file)
            files_vdb.append({"name":file_vdb})

        print(files_vdb)
        file0 = files[0]

        bpy.ops.object.volume_import(filepath=file0,
                                     directory=os.path.dirname(file0), 
                                     files=files_vdb,
                                     relative_path=False, 
                                     align='WORLD', 
                                     location=(0, 0, 0), 
                                     scale=(1, 1, 1))

        bpy.ops.transform.resize(value=(1/scale_factor, 1/scale_factor, 1/scale_factor))
        bpy.ops.transform.translate(value=offset)

        return {"FINISHED"}

class IntuitionRF_OT_plot_port_return_loss(IntuitionRF_returnloss_plotter):
    """Run the currently defined simulation in OpenEMS"""
    bl_idname = "intuitionrf.plot_port_return_loss"
    bl_label = "Plot s11(dB)"

    def execute(self, context):
        active_port = bpy.context.view_layer.objects.active 
        if not active_port.intuitionRF_properties.object_type == "port":
            self.report({'INFO'}, "Cannot plot impedance : not a port")

        port = ports[active_port.name]

        self.plot_s11(port, context)

        return {"FINISHED"}

class IntuitionRF_OT_plot_return_loss(IntuitionRF_returnloss_plotter):
    """Run the currently defined simulation in OpenEMS"""
    bl_idname = "intuitionrf.plot_return_loss"
    bl_label = "Plot s11(dB)"

    def execute(self, context):
        active_port = ports[context.scene.intuitionRF_port_selector]

        self.plot_s11(active_port, context)

        return {"FINISHED"}


def PEC_dump_to_scene(filename, context):
    if context.scene.intuitionRF_PEC_dump is not None:
        bpy.data.objects.remove(bpy.context.scene.intuitionRF_PEC_dump, do_unlink=True)
    coords, indices = extract_lines_from_vtp(filename)

    mesh = bpy.data.meshes.new("PEC_dump")  # add a new mesh
    PEC_dump = bpy.data.objects.new("PEC_dump", mesh)  # add a new object using the mesh
    bpy.context.collection.objects.link(PEC_dump)
    bpy.context.view_layer.objects.active = PEC_dump

    unit = context.scene.intuitionRF_unit
    coords = [(coord[0]/unit, coord[1]/unit, coord[2]/unit) for coord in coords]

    mesh.from_pydata(coords, indices, [])
    PEC_dump.show_in_front = True

    context.scene.intuitionRF_PEC_dump = PEC_dump

# Function to read the VTP file and extract line data
# this function was entirely generated by LLM
def extract_lines_from_vtp(filename):
    # Create a reader for the VTP file
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    # Get the polydata from the reader
    polydata = reader.GetOutput()

    # Check if the polydata contains lines
    if polydata.GetNumberOfLines() == 0:
        print("No lines found in the VTP file.")
        return

    # Extract points and lines
    points = polydata.GetPoints()
    lines = polydata.GetLines()

    # Get the number of points
    num_points = points.GetNumberOfPoints()

    # Get the number of lines
    num_lines = lines.GetNumberOfCells()

    # Retrieve point coordinates
    point_coords = []
    for i in range(num_points):
        point_coords.append(points.GetPoint(i))

    # Retrieve line connectivity
    lines.InitTraversal()
    id_list = vtk.vtkIdList()
    line_connectivity = []
    for i in range(num_lines):
        lines.GetNextCell(id_list)
        line = []
        for j in range(id_list.GetNumberOfIds()):
            line.append(id_list.GetId(j))
        line_connectivity.append(line)

    return point_coords, line_connectivity

def start_stop_from_BB(bound_box):
    min_x = min(round(vert[0], 5) for vert in bound_box)
    min_y = min(round(vert[1], 5) for vert in bound_box)
    min_z = min(round(vert[2], 5) for vert in bound_box)
    max_x = max(round(vert[0], 5) for vert in bound_box)
    max_y = max(round(vert[1], 5) for vert in bound_box)
    max_z = max(round(vert[2], 5) for vert in bound_box)

    return [min_x, min_y, min_z], [max_x, max_y, max_z]

def get_axis(verts):
    """Determine the normal of verts located inside and axis aligned plane"""
    v0 = verts[0] 
    x = True 
    y = True 
    z = True

    margin = .0001

    for vert in verts[1:]:
        if abs(vert[0] - v0[0]) > margin:
            x = False
        if abs(vert[1] - v0[1]) > margin:
            y = False
        if abs(vert[2] - v0[2]) > margin:
            z = False

    if x:
        #transpose/slice without numpy
        a0 = [v[1] for v in verts]
        a1 = [v[2] for v in verts]
        return 'x', v0[0], [a0, a1]
    elif y:
        a0 = [v[0] for v in verts]
        a1 = [v[2] for v in verts]
        return 'y', v0[1], [a1, a0]
    elif z:
        a0 = [v[0] for v in verts]
        a1 = [v[1] for v in verts]
        return 'z', v0[2], [a0, a1]
    else: 
        return 'None', None, None
    

def objects_from_scene(FDTD, CSX, context):
    """Exports relevant objects into the continous structure """
    objects_collection = context.scene.intuitionRF_objects.objects

    for o in objects_collection:
        if o.intuitionRF_properties.object_type == "metal_aa_faces":
            polygons = o.data.polygons
            vertices = o.data.vertices

            for index, polygon in enumerate(polygons):
                # add a CSX polygon each 
                # improvement: use single polygon for convex continuous same-normal polygon sets
                local_verts = [vertices[polygon.vertices[i]].co for i in range(len(polygon.vertices))]
                co = [[round(i[0], 5), 
                       round(i[1], 5), 
                       round(i[2], 5)] for i in local_verts]
                normal, elevation, points = get_axis(co)
                if normal != "None":
                    metal = CSX.AddMetal(f"{o.name}_{index}")
                    prim = metal.AddPolygon(points, normal, elevation)
                    prim.SetPriority(10)
                    dirs = 'xyz'.replace(normal, '')
                    mesh_res = context.scene.intuitionRF_smooth_mesh
                    #FDTD.AddEdges2Grid(dirs=dirs, properties=metal, metal_edge_res=mesh_res/2)

        # export metals (volume)
        if o.intuitionRF_properties.object_type == "metal_volume":
            filename = f"{context.scene.intuitionRF_simdir}/{o.name}.stl"
            bpy.ops.object.select_all(action='DESELECT')
            o.select_set(True)

            unit = context.scene.intuitionRF_unit
            # fix for blender 4.2
            #bpy.ops.export_mesh.stl(filepath=filename, ascii=True, use_selection=True)
            bpy.ops.wm.stl_export(filepath=filename, ascii_format=True, export_selected_objects=True)

            # immediately reimport mesh as a CSX metal part
            metal = CSX.AddMetal(o.name)
            # import STL file
            #
            start, stop = start_stop_from_BB(o.bound_box)
            #metal.AddBox(start, stop)
            reader = metal.AddPolyhedronReader(filename)
            reader.SetPriority(10)
            reader.SetFileType(1) # 1 STL, 2 PLY 
            reader.ReadFile()
            reader.Update()
            reader.SetPrimitiveUsed(True)

        if o.intuitionRF_properties.object_type == "metal_edges":
            edges = o.data.edges
            vertices = o.data.vertices

            metal = CSX.AddMetal(o.name)

            for index, edge in enumerate(edges):
                # TODO rounding
                v0 = vertices[edge.vertices[0]].co
                v1 = vertices[edge.vertices[1]].co

                coords = np.array([v0, v1])
                metal.AddCurve(coords.T)

        if o.intuitionRF_properties.object_type == "dumpbox":
            start, stop = start_stop_from_BB(o.bound_box)
            # TODO make this cacheable
             
            filename_prefix = f"{context.scene.intuitionRF_simdir}/{o.name}"
            # remove any previously existing files
            for f in glob.glob(f"{filename_prefix}*"):
                os.remove(f)

            dumpbox = CSX.AddDump(filename_prefix)
            dumpbox.SetDumpType(int(o.intuitionRF_properties.dump_type))
            dumpbox.SetDumpMode(int(o.intuitionRF_properties.dump_mode))
            dumpbox.AddBox(start, stop)

        if o.intuitionRF_properties.object_type == "material":
            filename = f"{context.scene.intuitionRF_simdir}/{o.name}.stl"
            bpy.ops.object.select_all(action='DESELECT')
            o.select_set(True)
            #bpy.ops.export_mesh.stl(filepath=filename, ascii=True, use_selection=True)
            bpy.ops.wm.stl_export(filepath=filename, ascii_format=True, export_selected_objects=True)

            # immediately reimport mesh as a CSX metal part
            if o.intuitionRF_properties.material_use_kappa:
                material = CSX.AddMaterial(
                    o.name, 
                    epsilon = o.intuitionRF_properties.material_epsilon,
                    kappa = o.intuitionRF_properties.material_kappa
                )
            else:
                material = CSX.AddMaterial(
                    o.name, 
                    epsilon = o.intuitionRF_properties.material_epsilon,
                )
            # import STL file
            #
            start, stop = start_stop_from_BB(o.bound_box)
            #metal.AddBox(start, stop)
            reader = material.AddPolyhedronReader(filename)
            reader.SetFileType(1) # 1 STL, 2 PLY 
            reader.ReadFile()
            reader.Update()
            reader.SetPrimitiveUsed(True)

        # might night to change name later to account for making modifiers used in the setup
        # (not currently the case)
        if o.intuitionRF_properties.object_type == "geometry_node":
            depsgraph = context.evaluated_depsgraph_get()
            evaluated_obj = o.evaluated_get(depsgraph)

            # now we look for vertices flagged with known attributes
            attributes = evaluated_obj.data.attributes

            for attribute in attributes:
                if attribute.name == "intuitionrf.port_index":
                    ports_from_geometry_nodes(evaluated_obj, FDTD, CSX)

                if attribute.name == "intuitionrf.pec_edge":
                    pec_edges_from_geometry_nodes(evaluated_obj, FDTD, CSX)

                if attribute.name == "intuitionrf.pec_aa_face":
                    pec_aa_faces_from_geometry_nodes(evaluated_obj, FDTD, CSX)

                if attribute.name == "intuitionrf.pec_volume":
                    pec_volume_from_geometry_nodes(evaluated_obj, context, FDTD, CSX)

                if attribute.name == "intuitionrf.epsilonr":
                    material_from_geometry_nodes(evaluated_obj, context, FDTD, CSX)

    # needed to add ports after every other element
    # TODO handle ports defined in geometry nodes
    for o in objects_collection:
        if o.intuitionRF_properties.object_type == "port":
            start, stop = start_stop_from_BB(o.bound_box)
            impedance = o.intuitionRF_properties.port_impedance
            port_number = o.intuitionRF_properties.port_number
            direction = o.intuitionRF_properties.port_direction
            excite = 1.0 if o.intuitionRF_properties.port_active else 0.0 
            port = FDTD.AddLumpedPort(port_number, impedance, 
                start, stop, direction, excite)

            ports[o.name] = port

    return FDTD, CSX 

def material_from_geometry_nodes(evaluated_obj, context, FDTD, CSX):
    pass

    # sort materials according to their use of kappa, epsilon and (optional) kappa values
    # assume the presence of 'use_kappa' and 'kappa' if 'epsilonR' present
    material_data =  zip(evaluated_obj.data.polygons, 
                         evaluated_obj.data.attributes['intuitionrf.epsilonr'].data,
                         evaluated_obj.data.attributes['intuitionrf.use_kappa'].data,
                         evaluated_obj.data.attributes['intuitionrf.kappa'].data
                         )
    # filter out 0-epsilonR materials (epsilonR = 0 isn't possible and is use to mark faces as not part of a material)
    material_data = [item for item in material_data if item[1].value != 0]

    materials = defaultdict(lambda: [])
    for index, item in enumerate(material_data):
        # we will have a tuple as the key here because we don't want to nest the 
        # dictionnary output
        materials[(item[1].value, item[2].value, item[3].value)].append(item[0])

    # now for each material we found we export the STL
    # and reimport it into OpenEMS immediately
    # TODO de-duplicate this whole export STL section
    for index, (key, polygons) in enumerate(materials.items()):
        epsilonR = key[0]
        use_kappa = key[1]
        kappa = key[2]
        
        mesh = bpy.data.meshes.new(f"{evaluated_obj.name}.material.{index}.tmp")
        obj = bpy.data.objects.new(f"{evaluated_obj.name}.material.{index}.tmp", mesh)

        # add all vertices from the source object, just not all the faces
        # this will litter the tmp object with potentially unused vertices 
        # but they will be lost on stl export (terrible solution, but it works)
        # which avoids rewriting all face vertices indices
        # In this case rounding vertex coords is not curcially important because 
        # it is meant to be evaluated as a mesh anyway
        vertices = [item.co for item in evaluated_obj.data.vertices]
        faces = []

        for polygon in polygons:
            faces.append(polygon.vertices)

        mesh.from_pydata(vertices, [], faces)
        mesh.update()

        context.collection.objects.link(obj)

        filename = f"{context.scene.intuitionRF_simdir}/{evaluated_obj.name}.material.{index}.stl"
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        #bpy.ops.export_mesh.stl(filepath=filename, ascii=True, use_selection=True)
        bpy.ops.wm.stl_export(filepath=filename, ascii_format=True, export_selected_objects=True)

        if use_kappa:
            material = CSX.AddMaterial(
                f"{evaluated_obj.name}.material.{index}",
                epsilon = epsilonR,
                kappa = kappa,
            )
        else:
            material = CSX.AddMaterial(
                f"{evaluated_obj.name}.material.{index}",
                epsilon = epsilonR,
            )

        reader = material.AddPolyhedronReader(filename)
        reader.SetFileType(1) # 1 STL, 2 PLY 
        reader.ReadFile()
        reader.Update()
        reader.SetPrimitiveUsed(True)

        bpy.data.objects.remove(obj, do_unlink=True)


def pec_volume_from_geometry_nodes(evaluated_obj, context, FDTD, CSX):
    # need to 
    # - create a new object, 
    # - populate it with the data, 
    # - export stl, 
    # - delete object and 
    # - reimport object

    # now extract the vertices and faces if interest and then put them into the new object 
    # there is probably a better way to achieve this
    pec_data = zip(evaluated_obj.data.polygons, evaluated_obj.data.attributes['intuitionrf.pec_volume'].data)

    # filter out faces of interest
    pec_data = [item for item in pec_data if item[1].value == True]
    if len(pec_data) == 0:
        return 

    mesh = bpy.data.meshes.new(f"{evaluated_obj.name}.pec_volume.tmp")
    obj = bpy.data.objects.new(f"{evaluated_obj.name}.pec_volume.tmp", mesh)

    # add all vertices from the source object, just not all the faces
    # this will litter the tmp object with potentially unused vertices 
    # but they will be lost on stl export (terrible solution, but it works)
    # which avoids rewriting all face vertices indices
    # In this case rounding vertex coords is not curcially important because 
    # it is meant to be evaluated as a mesh anyway
    vertices = [item.co for item in evaluated_obj.data.vertices]
    faces = []
    for index, item in enumerate(pec_data):
        polygon = item[0].vertices

        faces.append(polygon)

    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    context.collection.objects.link(obj)

    filename = f"{context.scene.intuitionRF_simdir}/{evaluated_obj.name}.metal_volume.stl"
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    #bpy.ops.export_mesh.stl(filepath=filename, ascii=True, use_selection=True)
    bpy.ops.wm.stl_export(filepath=filename, ascii_format=True, export_selected_objects=True)

    # immediately reimport mesh as a CSX metal part
    metal = CSX.AddMetal(f"{evaluated_obj.name}.pec_volume")

    reader = metal.AddPolyhedronReader(filename)
    reader.SetPriority(10)
    reader.SetFileType(1) # 1 STL, 2 PLY 
    reader.ReadFile()
    reader.Update()
    reader.SetPrimitiveUsed(True)

    bpy.data.objects.remove(obj, do_unlink=True)

def pec_aa_faces_from_geometry_nodes(evaluated_obj, FDTD, CSX):
    pec_data = zip(evaluated_obj.data.polygons, evaluated_obj.data.attributes['intuitionrf.pec_aa_face'].data)

    # filter out the faces we need
    pec_data = [item for item in pec_data if item[1].value == True]
    if len(pec_data) == 0:
        return

    for index, item in enumerate(pec_data):
        # extract vertices from PEC face

        # TODO de-duplicate this code from the objects aa face from destructive 
        # topology
        polygon = item[0]
        vertices = evaluated_obj.data.vertices
        local_verts = [vertices[polygon.vertices[i]].co for i in range(len(polygon.vertices))]
        co = [[round(i[0], 5), 
                round(i[1], 5), 
                round(i[2], 5)] for i in local_verts]
        normal, elevation, points = get_axis(co)

        if normal != "None":
            metal = CSX.AddMetal(f"{evaluated_obj.name}.pec_aa_face.{index}")
            prim = metal.AddPolygon(points, normal, elevation)
            prim.SetPriority(10)

def pec_edges_from_geometry_nodes(evaluated_obj, FDTD, CSX):
    pec_data = zip(evaluated_obj.data.edges, evaluated_obj.data.attributes['intuitionrf.pec_edge'].data)


    # filter out any list with no pec edges at all 
    # such as not to add empty curve primitives to the SIM
    pec_data = [item for item in pec_data if item[1].value == True]
    if len(pec_data) == 0:
        return

    metal = CSX.AddMetal(f"{evaluated_obj.name}.edges")

    for item in pec_data:

        v0 = evaluated_obj.data.vertices[item[0].vertices[0]].co 
        v1 = evaluated_obj.data.vertices[item[0].vertices[1]].co

        # round coords 
        v0[0] = round(v0[0], 5)
        v0[1] = round(v0[1], 5)
        v0[2] = round(v0[2], 5)
        v1[0] = round(v1[0], 5)
        v1[1] = round(v1[1], 5)
        v1[2] = round(v1[2], 5)
        coords = np.array([v0, v1])
        metal.AddCurve(coords.T)


def ports_from_geometry_nodes(evaluated_obj, FDTD, CSX):
    # assume other required attributes are defined aswell 
    # (user didn't add store named attribute node of name 'intuitionrf.port_index')
    
    port_data = zip(evaluated_obj.data.vertices, 
        evaluated_obj.data.attributes['intuitionrf.port_index'].data, 
        evaluated_obj.data.attributes['intuitionrf.port_impedance'].data, 
        evaluated_obj.data.attributes['intuitionrf.port_axis'].data, 
        evaluated_obj.data.attributes['intuitionrf.port_active'].data 
        )

    port_dict = defaultdict(lambda: []) # map each port data by the port index
    # ports[index] = [(vertex, impedance, axis, active), (vertex, impedance, axis, active), ...]
    for item in port_data:
        if item[1].value == 0: # invalid port index 
            continue
        # we want to extract the actual float values from the nested data structures here for 
        # further processing
        port_dict[item[1].value].append(list(tuple(
            (
                # x,y,z coords of the point
                round(item[0].co[0], 5), 
                round(item[0].co[1], 5),
                round(item[0].co[2], 5),
                item[2].value, 
                # x, y, z coords of the orientation at the point
                round(item[3].vector[0], 5), 
                round(item[3].vector[1], 5), 
                round(item[3].vector[2], 5), 
                item[4].value
            )
        )))

    # now we find for each port the average orienation vector, average active value, etc.. 
    for key, value in port_dict.items(): 
        value = np.array(value)
        min_x, min_y, min_z = (np.min(value[:,0]), np.min(value[:,1]), np.min(value[:,2]))
        max_x, max_y, max_z = (np.max(value[:,0]), np.max(value[:,1]), np.max(value[:,2]))
        axis_x, axis_y, axis_z = (np.mean(value[:,4]), np.mean(value[:,5]), np.mean(value[:,6]))
        axis_x, axis_y, axis_z = (abs(axis_x), abs(axis_y), abs(axis_z))
        axis = "x"
        if axis_y > axis_x and axis_y > axis_z:
            axis = 'y'
        if axis_z > axis_x and axis_z > axis_y:
            axis = 'z'

        impedance = np.mean(value[:,3])
        active = float(np.mean(value[:,7]) > 0)

        port = FDTD.AddLumpedPort(key, impedance, 
            [min_x, min_y, min_z], [max_x, max_y, max_z], axis, active)

        # register it in the port list for later processing
        ports[str(key)] = port

def meshlines_from_scene(CSX, context):
    lines = context.scene.intuitionRF_lines
    x, y, z = extract_lines_xyz(lines)
    
    mesh = CSX.GetGrid()
    unit = context.scene.intuitionRF_unit
    mesh.SetDeltaUnit(unit)

    # put lines in CSXCAD        
    mesh.AddLine('x', list(x))
    mesh.AddLine('y', list(y))
    mesh.AddLine('z', list(z))

    # also extract lines from objects
    CSX = meshlines_from_vertex_groups(CSX, context)

    # smooth as required by user
    if context.scene.intuitionRF_smooth_mesh:
        # smooth all directions the same
        # per grid granularty should be determiner by fixed lines 
        # (easy to place graphically)
        mesh.SmoothMeshLines('x', context.scene.intuitionRF_smooth_max_res, context.scene.intuitionRF_smooth_ratio)
        mesh.SmoothMeshLines('y', context.scene.intuitionRF_smooth_max_res, context.scene.intuitionRF_smooth_ratio)
        mesh.SmoothMeshLines('z', context.scene.intuitionRF_smooth_max_res, context.scene.intuitionRF_smooth_ratio)        
        pass
    return CSX

def meshlines_from_vertex_groups(CSX, context):
    # extract list of coordinates from vertex group named 'intuitionRF_verts'
    x = set() 
    y = set()
    z = set()

    objects_collection = context.scene.intuitionRF_objects.objects
    for o in objects_collection:
        # dump box need no meshing an neither do "None"
        if o.intuitionRF_properties.object_type == "dumpbox":
            continue
        if o.intuitionRF_properties.object_type == "none":
            continue
        # skip objects that have no anchors assigned
        if "intuitionRF_anchors" not in o.vertex_groups:
            continue

        # need to iterate over all vertices and check their weight in the group
        intuitionRF_vgroup = o.vertex_groups['intuitionRF_anchors'].index
        verts = o.data.vertices
        for v in verts:
            weights = [group.weight for group in v.groups if group.group == intuitionRF_vgroup]
            # check in group, any nonzero weight will do
            if len(weights) == 1 and weights[0] != 0: 
                
                x.add(v.co[0])
                y.add(v.co[1])
                z.add(v.co[2])

    # TODO loop the collection only once
    for o in objects_collection:
        # we also want to extract vertices from named attributes stored in geometry nodes
        # TODO merge this with the above as to apply modifiers everywhere
        dg = context.evaluated_depsgraph_get()
        evaluated_object = o.evaluated_get(dg)
        attr_anchors = [attr for attr in evaluated_object.data.attributes if attr.name == "intuitionrf.anchor"]
        if len(attr_anchors) == 1:
            attr_anchors = attr_anchors[0]
            for i, v in enumerate(evaluated_object.data.vertices):
                if attr_anchors.data[i].value == True:

                    x.add(round(v.co[0], 5)) 
                    y.add(round(v.co[1], 5))
                    z.add(round(v.co[2], 5))

    mesh = CSX.GetGrid()
    # put lines in CSXCAD        
    if len(list(x)) > 0:
        mesh.AddLine('x', list(sorted(x)))
        mesh.AddLine('y', list(sorted(y)))
        mesh.AddLine('z', list(sorted(z)))

    return CSX
        
class IntuitionRF_OT_add_preview_lines(bpy.types.Operator):
    """ Add openEMS meshing lines preview """
    bl_idname = "intuitionrf.add_preview_lines"
    bl_label = "Add meshing lines preview"
    
    def execute(self, context):
        if context.scene.intuitionRF_previewlines is not None:
            bpy.data.objects.remove(bpy.context.scene.intuitionRF_previewlines, do_unlink=True)

        FDTD = openEMS(NrTS=1, EndCriteria=1e-4)

        CSX = CSXCAD.ContinuousStructure()
        CSX = meshlines_from_scene(CSX, context)
        FDTD.SetCSX(CSX)
        FDTD.SetGaussExcite( context.scene.center_freq * 1e6, context.scene.cutoff_freq * 1e6)
        FDTD.SetBoundaryCond( ['MUR', 'MUR', 'MUR', 'MUR', 'MUR', 'MUR'] )

        FDTD, CSX = objects_from_scene(FDTD, CSX, context)
        mesh = CSX.GetGrid()
        
        # retrieve lines
        x = mesh.GetLines('x')
        y = mesh.GetLines('y')
        z = mesh.GetLines('z')

        unit = context.scene.intuitionRF_unit

        # create a new mesh
        mesh = bpy.data.meshes.new("preview_lines")  # add a new mesh
        preview_lines = bpy.data.objects.new("preview_lines", mesh)  # add a new object using the mesh
        bpy.context.collection.objects.link(preview_lines)
#        bpy.context.view_layer.objects.active = preview_lines
        
        # draw lines in each directions         
        verts = []
        edges = []
        faces = []
        for item_x in x:
            # draw lines at min_y from min_z to mzx_z
            verts.append(tuple((item_x, min(y), min(z))))
            verts.append(tuple((item_x, min(y), max(z))))
            # add the latest two vertices to a new edge
            edges.append([len(verts) - 1, len(verts) - 2])
            # draw bottom lines
            verts.append(tuple((item_x, min(y), min(z))))
            verts.append(tuple((item_x, max(y), min(z))))
            edges.append([len(verts) - 1, len(verts) - 2])
            
        for item_y in y:
            verts.append(tuple((min(x), item_y, min(z))))
            verts.append(tuple((min(x), item_y, max(z))))
            edges.append([len(verts) - 1, len(verts) - 2])
            verts.append(tuple((min(x), item_y, min(z))))
            verts.append(tuple((max(x), item_y, min(z))))
            edges.append([len(verts) - 1, len(verts) - 2])
            
        for item_z in z:
            verts.append(tuple((min(x), min(y), item_z)))
            verts.append(tuple((max(x), min(y), item_z)))
            edges.append([len(verts) - 1, len(verts) - 2])
            verts.append(tuple((min(x), min(y), item_z)))
            verts.append(tuple((min(x), max(y), item_z)))
            edges.append([len(verts) - 1, len(verts) - 2])

        mesh.from_pydata(verts, edges, faces)
        mesh.validate(verbose=True)
        preview_lines.show_name = True
        preview_lines.hide_select = True
        context.scene.intuitionRF_previewlines = preview_lines
        return {"FINISHED"}

def register():
    bpy.utils.register_class(IntuitionRF_OT_add_meshline_x)
    bpy.utils.register_class(IntuitionRF_OT_add_meshline_y)    
    bpy.utils.register_class(IntuitionRF_OT_add_meshline_z)    

    bpy.utils.register_class(IntuitionRF_OT_add_domain)
    bpy.utils.register_class(IntuitionRF_OT_add_wavelength_cube)
    bpy.utils.register_class(IntuitionRF_OT_add_default_lines)
    bpy.utils.register_class(IntuitionRF_OT_add_preview_lines)

    bpy.utils.register_class(IntuitionRF_OT_preview_CSX)
    bpy.utils.register_class(IntuitionRF_OT_preview_PEC_dump)
    bpy.utils.register_class(IntuitionRF_OT_run_sim)
    bpy.utils.register_class(IntuitionRF_OT_plot_port_return_loss)
    bpy.utils.register_class(IntuitionRF_OT_plot_return_loss)
    bpy.utils.register_class(IntuitionRF_OT_plot_port_impedance)
    bpy.utils.register_class(IntuitionRF_OT_plot_impedance)
    bpy.utils.register_class(IntuitionRF_OT_compute_NF2FF)
    bpy.utils.register_class(IntuitionRF_OT_check_updates)

    bpy.utils.register_class(IntuitionRF_OT_convert_volume_single_frame)
    bpy.utils.register_class(IntuitionRF_OT_convert_volume_all_frames)

def unregister():
    bpy.utils.unregister_class(IntuitionRF_OT_add_meshline_x)
    bpy.utils.unregister_class(IntuitionRF_OT_add_meshline_y)    
    bpy.utils.unregister_class(IntuitionRF_OT_add_meshline_z)    

    bpy.utils.unregister_class(IntuitionRF_OT_add_domain)
    bpy.utils.unregister_class(IntuitionRF_OT_add_default_lines)
    bpy.utils.unregister_class(IntuitionRF_OT_add_preview_lines)
    bpy.utils.unregister_class(IntuitionRF_OT_add_wavelength_cube)

    bpy.utils.unregister_class(IntuitionRF_OT_preview_CSX)
    bpy.utils.unregister_class(IntuitionRF_OT_preview_PEC_dump)
    bpy.utils.unregister_class(IntuitionRF_OT_run_sim)
    bpy.utils.unregister_class(IntuitionRF_OT_plot_port_return_loss)
    bpy.utils.unregister_class(IntuitionRF_OT_plot_return_loss)
    bpy.utils.unregister_class(IntuitionRF_OT_plot_port_impedance)
    bpy.utils.unregister_class(IntuitionRF_OT_plot_impedance)
    bpy.utils.unregister_class(IntuitionRF_OT_compute_NF2FF)
    bpy.utils.unregister_class(IntuitionRF_OT_check_updates)
