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
import IPython

# workaround a bug in vtk/or python interpreter bundled with blender 
from unittest.mock import MagicMock
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
            print(verts[edge.vertices[0]].co[2])
            print(verts[edge.vertices[1]].co[2])            
        
    return (x, y, z)

def add_meshline(context, direction):
    bpy.ops.object.mode_set(mode='OBJECT')
    # backup which object we're currently editing
    source_object = context.view_layer.objects.active
    
    # backup source selected vertices to slice at
    source_selected_verts = [v for v in bpy.context.active_object.data.vertices if v.select]
    
    bm = bmesh.new()
    bm.from_mesh(context.scene.intuitionRF_lines.data)
    print(bm.edges)
    
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
                    print("Found unique intersection")
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
        global nf2ff
        FDTD = openEMS(NrTS=1e6, EndCriteria=1e-4)

        CSX = CSXCAD.ContinuousStructure()
        CSX = meshlines_from_scene(CSX, context)
        FDTD.SetCSX(CSX)
        FDTD.SetGaussExcite( context.scene.center_freq * 1e6, context.scene.cutoff_freq * 1e6)
        FDTD.SetBoundaryCond( ['MUR', 'MUR', 'MUR', 'MUR', 'MUR', 'MUR'] )

        FDTD, CSX = objects_from_scene(FDTD, CSX, context)

        mesh = CSX.GetGrid()
        mesh_res = context.scene.intuitionRF_smooth_max_res
        mesh.SmoothMeshLines('all', mesh_res, 1.4)

        # Add the nf2ff recording box
        nf2ff = FDTD.CreateNF2FFBox()

        FDTD.Run(sim_path=context.scene.intuitionRF_simdir, cleanup=False)
        
        return {"FINISHED"}

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
        rad_pat = bpy.data.objects.new("radiation_pattern", mesh)  # add a new object using the mesh
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

class IntuitionRF_OT_plot_port_impedance(bpy.types.Operator):
    """Run the currently defined simulation in OpenEMS"""
    bl_idname = "intuitionrf.plot_port_impedance"
    bl_label = "Plot Impedance"

    def execute(self, context):
        active_port = bpy.context.view_layer.objects.active 
        if not active_port.intuitionRF_properties.object_type == "port":
            self.report({'INFO'}, "Cannot plot impedance : not a port")

        port = ports[active_port.name]

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

        return {"FINISHED"}

class IntuitionRF_OT_plot_port_return_loss(bpy.types.Operator):
    """Run the currently defined simulation in OpenEMS"""
    bl_idname = "intuitionrf.plot_port_return_loss"
    bl_label = "Plot s11(dB)"

    def execute(self, context):
        active_port = bpy.context.view_layer.objects.active 
        if not active_port.intuitionRF_properties.object_type == "port":
            self.report({'INFO'}, "Cannot plot impedance : not a port")

        port = ports[active_port.name]

        f0 = context.scene.center_freq * 1e6 
        fc = context.scene.cutoff_freq * 1e6
        f = np.linspace(f0-fc,f0+fc,601)
        try:
            port.CalcPort(context.scene.intuitionRF_simdir, f)
        except:
            self.report({'INFO'}, "Failed to calc port")

        Zin = port.uf_tot / port.if_tot
        s11 = port.uf_ref/port.uf_inc
        s11_dB = 20.0*np.log10(np.abs(s11))

        plt.plot(f/1e6, s11_dB)
        plt.ylabel('s11 (dB)')
        plt.xlabel('f (MHz)')
        plt.grid()
        plt.show()

        # put resonnant frequency to the scene res. freq 
        # multiple port not handled yet
        res_freq = f[np.argmin(s11_dB)] / 1e6
        context.scene.intuitionRF_resonnant_freq = res_freq

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
    for vert in bound_box:
        print(vert)
    min_x = min(vert[0] for vert in bound_box)
    min_y = min(vert[1] for vert in bound_box)
    min_z = min(vert[2] for vert in bound_box)
    max_x = max(vert[0] for vert in bound_box)
    max_y = max(vert[1] for vert in bound_box)
    max_z = max(vert[2] for vert in bound_box)

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
                co = [[i[0], i[1], i[2]] for i in local_verts]
                normal, elevation, points = get_axis(co)
                if normal != "None":
                    print(points)
                    print(normal)
                    print(elevation)
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
            bpy.ops.export_mesh.stl(filepath=filename, ascii=True, use_selection=True)

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

        if o.intuitionRF_properties.object_type == "dumpbox":
            print("Found dumpbox")
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
            bpy.ops.export_mesh.stl(filepath=filename, ascii=True, use_selection=True)

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

    #f0 = 146e6 # center frequency, frequency of interest!
    #lambda0 = int(C0/f0) # wavelength in mm
    #nf2ff = FDTD.CreateNF2FFBox(opt_resolution=[lambda0/15]*3)


    return FDTD, CSX 

def meshlines_from_scene(CSX, context):
    lines = context.scene.intuitionRF_lines
    x, y, z = extract_lines_xyz(lines)
    print("extracted lines")
    print(x)
    print(y)
    print(z)
    
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
                print(v.co)
                
                x.add(v.co[0])
                y.add(v.co[1])
                z.add(v.co[2])

    print(x)
    print(y)
    print(z)
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
        # print(f"x = {x}")
        # print(f"y = {y}")
        # print(f"z = {z}")

        unit = context.scene.intuitionRF_unit
        print(len(x))
        print(len(y))
        print(len(z))

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
    bpy.utils.register_class(IntuitionRF_OT_plot_port_impedance)
    bpy.utils.register_class(IntuitionRF_OT_compute_NF2FF)

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
    bpy.utils.unregister_class(IntuitionRF_OT_plot_port_impedance)
    bpy.utils.unregister_class(IntuitionRF_OT_compute_NF2FF)
