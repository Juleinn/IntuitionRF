bl_info = {
    "name": "IntuitionRF an OpenEMS wrapper for blender",
    "blender": (2, 80, 0),
    "category": "Object",
}

import bpy 
import sys
import bmesh
import mathutils
from mathutils import geometry

syspath = ['', '/home/anton/code/python/libs', '/usr/local/lib/python311.zip', '/usr/local/lib/python3.11', '/usr/local/lib/python3.11/lib-dynload', '/home/anton/.local/lib/python3.11/site-packages', '/home/anton/.local/lib/python3.11/site-packages/CSXCAD-0.6.2-py3.11-linux-x86_64.egg', '/home/anton/.local/lib/python3.11/site-packages/openEMS-0.0.36-py3.11-linux-x86_64.egg', '/usr/local/lib/python3.11/site-packages']
for item in syspath:
    sys.path.append(item)

from CSXCAD import CSXCAD

from openEMS import openEMS
from openEMS.physical_constants import *

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
    
class IntuitionRF_OT_add_preview_lines(bpy.types.Operator):
    """ Add openEMS meshing lines preview """
    bl_idname = "intuitionrf.add_preview_lineslines"
    bl_label = "Add meshing lines preview"
    
    def execute(self, context):
        if context.scene.intuitionRF_previewlines is not None:
            bpy.data.objects.remove(bpy.context.scene.intuitionRF_previewlines, do_unlink=True)
        
        lines = context.scene.intuitionRF_lines
        x, y, z = extract_lines_xyz(lines)
        
        FDTD = openEMS(EndCriteria=1e-4)
        f0 = context.scene.center_freq
        fc = context.scene.cutoff_freq
        if context.scene.intuitionRF_excitation_type == "gauss":
            FDTD.SetGaussExcite(f0, fc)
        else:
            FDTD.SetSineExcite(f0)
        # TODO handle boundary conditions
        FDTD.SetBoundaryCond( ['MUR', 'MUR', 'MUR', 'MUR', 'MUR', 'MUR'] )

        CSX = CSXCAD.ContinuousStructure()
        FDTD.SetCSX(CSX)
        mesh = CSX.GetGrid()
        unit = context.scene.intuitionRF_unit
        mesh.SetDeltaUnit(unit)

        # put lines in CSXCAD        
        mesh.AddLine('x', list(x))
        mesh.AddLine('y', list(y))
        mesh.AddLine('z', list(z))
        # smooth as required by user
        if context.scene.intuitionRF_smooth_mesh:
            # smooth all directions the same
            # per grid granularty should be determiner by fixed lines 
            # (easy to place graphically)
            mesh.SmoothMeshLines('x', context.scene.intuitionRF_smooth_max_res, context.scene.intuitionRF_smooth_ratio)
            mesh.SmoothMeshLines('y', context.scene.intuitionRF_smooth_max_res, context.scene.intuitionRF_smooth_ratio)
            mesh.SmoothMeshLines('z', context.scene.intuitionRF_smooth_max_res, context.scene.intuitionRF_smooth_ratio)        
            
        # retrieve lines
        x = mesh.GetLines('x')
        y = mesh.GetLines('y')
        z = mesh.GetLines('z')
        print(f"x = {x}")
        print(f"y = {y}")
        print(f"z = {z}")
                        
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
        preview_lines.show_name = True
        preview_lines.hide_select = True
        context.scene.intuitionRF_previewlines = preview_lines
        return {"FINISHED"}

class IntuitionRF(bpy.types.Menu):
    bl_label = "IntuitionRF"
    bl_idname = "OBJECT_MT_IntuitionRF"

    def draw(self, context):
        layout = self.layout

        layout.operator("intuitionrf.add_domain", text = "Add domain")

def draw_item(self, context):
    layout = self.layout
    layout.menu(IntuitionRF.bl_idname)


class IntuitionRFPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "IntuitionRF"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.prop(scene, "intuitionRF_unit")

        # Big render button
        layout.label(text="Add simulation domain")
        row = layout.row()
        row.scale_x = 1.0
        row.operator("intuitionrf.add_domain")
        row = layout.row()
        row.prop(scene, "intuitionRF_domain")
        
        layout.label(text="Excitation")
        row = layout.row()
        row.prop(scene, "intuitionRF_excitation_type")        
        row = layout.row()
        row.prop(scene, "center_freq")
        if context.scene.intuitionRF_excitation_type == "gauss":
            row = layout.row()
            row.prop(scene, "cutoff_freq")
        row = layout.row()
        row.prop(scene, "intuitionRF_objects")
        row = layout.row()
        wavelength = 300.0 / context.scene.center_freq
        row.label(text = f"\u03BB = {wavelength:.2}m" )
        row.operator("intuitionrf.add_wavelength_cube")
        row = layout.row()
        row = layout.row()
        row.prop(scene, "intuitionRF_lines")
        row = layout.row()
        row.operator("intuitionrf.add_default_lines")
        row = layout.row()
        row.prop(scene, "intuitionRF_smooth_mesh")
        row = layout.row()
        row.prop(scene, "intuitionRF_smooth_ratio")
        row = layout.row()
        row.prop(scene, "intuitionRF_smooth_max_res")
        row = layout.row()
        row.operator("intuitionrf.add_preview_lines")
        row = layout.row()
        row.operator("intuitionrf.add_meshline_x")
        row.operator("intuitionrf.add_meshline_y")
        row.operator("intuitionrf.add_meshline_z")
        
class IntuitionRF_ObjectProperties(bpy.types.PropertyGroup):
    object_type: bpy.props.EnumProperty(
        name = 'Type',
        description = 'Select an option', 
        items = [
            ('none', 'None', 'Ignored for computations'),
            ('PEC', 'PEC', 'perfect electrical conductor'),
            ('material', 'material (\u03B5,\u03BA)', 'material defined by \u03B5 and \u03BA'),
            ('dumpbox', 'Dump Box', 'Dump box for E or H fields (to be specified)'),
            ('nf2ff', 'NF2FF Box', 'Near Field to Far Field computation box'),
            ('port', 'Port', 'Excitation Port'),
        ]
    )
    # material properties
    material_epsilon: bpy.props.FloatProperty(name='\u03B5', default=4.6)
    material_use_kappa: bpy.props.BoolProperty(name='Use \u03BA', default=False)
    material_kappa: bpy.props.FloatProperty(name='\u03BA', default=2000)
    
    # port properties
    port_number: bpy.props.IntProperty(name='Port Number', default=1)
    port_impedance: bpy.props.FloatProperty(name='Impedance (ohms)', default=50)
    port_direction: bpy.props.EnumProperty(
        name = 'Direction',
        description = 'Port Excitation Direction', 
        items = [
            ('px', '+x', '+x'),
            ('py', '+y', '+y'),
            ('pz', '+z', '+z'),
            ('nx', '-x', '-x'),
            ('ny', '-y', '-y'),
            ('nz', '-z', '-z')
        ]
    )
    port_active: bpy.props.BoolProperty(name='Active', default=False)

# object tab properties panel
class OBJECT_PT_intuitionRFPanel(bpy.types.Panel):
    bl_label = "IntuitionRF object"
    bl_idname = "OBJECT_PT_intuitionRFPanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.object

        # Display the custom properties in the panel
        layout.prop(obj.intuitionRF_properties, "object_type")

        layout.separator()
        
        if obj.intuitionRF_properties.object_type == 'material':
            row = layout.row()
            row.prop(obj.intuitionRF_properties, "material_epsilon")    
            row = layout.row()
            row.prop(obj.intuitionRF_properties, "material_use_kappa")    
            if obj.intuitionRF_properties.material_use_kappa:
                row.prop(obj.intuitionRF_properties, "material_kappa")
        if obj.intuitionRF_properties.object_type == 'port':
            row = layout.row()
            row.prop(obj.intuitionRF_properties, "port_number")    
            row.prop(obj.intuitionRF_properties, "port_active")       
            row = layout.row()
            row.prop(obj.intuitionRF_properties, "port_impedance")    
            row = layout.row()
            row.prop(obj.intuitionRF_properties, "port_direction")       
        
def register():
    bpy.utils.register_class(IntuitionRFPanel)
    bpy.utils.register_class(IntuitionRF)
    bpy.types.VIEW3D_HT_header.append(draw_item)
    bpy.utils.register_class(IntuitionRF_OT_add_domain)
    bpy.utils.register_class(IntuitionRF_OT_add_wavelength_cube)
    bpy.utils.register_class(IntuitionRF_OT_add_default_lines)
    bpy.utils.register_class(IntuitionRF_OT_add_preview_lines)
    bpy.utils.register_class(IntuitionRF_OT_add_meshline_x)
    bpy.utils.register_class(IntuitionRF_OT_add_meshline_y)    
    bpy.utils.register_class(IntuitionRF_OT_add_meshline_z)    
    bpy.types.Scene.intuitionRF_unit = bpy.props.FloatProperty(
        name='Unit (scale)', 
        description = 
"""Blender to OpenEMS scaling factor. 
1e-3 means 1 blender unit (meter)
is 1mm in simulation""",
        default=1e-3
    )
    bpy.types.Scene.center_freq = bpy.props.FloatProperty(name='Center Freq (Mhz)', default=868.00)
    bpy.types.Scene.cutoff_freq = bpy.props.FloatProperty(name='Cutoff Freq (Mhz)', default=2*868.00)
    bpy.types.Scene.intuitionRF_objects = bpy.props.PointerProperty(type=bpy.types.Collection)
    bpy.types.Scene.intuitionRF_domain = bpy.props.PointerProperty(type=bpy.types.Object, name='Domain')
    bpy.types.Scene.intuitionRF_excitation_type = bpy.props.EnumProperty(
        name = '',
        description = 'Select an option', 
        items = [
            ('gauss', 'Gaussian', 'Gaussian Excite'),
            ('sine', 'Sine', 'Sine Excite')
        ]
    )
    bpy.types.Scene.intuitionRF_lines = bpy.props.PointerProperty(type=bpy.types.Object, name='lines')
    bpy.types.Scene.intuitionRF_smooth_mesh = bpy.props.BoolProperty(
        name="Smooth mesh lines",
        description="Smooth mesh lines",
        default = True
    )
    bpy.types.Scene.intuitionRF_previewlines = bpy.props.PointerProperty(type=bpy.types.Object, name='preview_lines')
    bpy.types.Scene.intuitionRF_smooth_max_res = bpy.props.FloatProperty(name='Smooth max resolution', default=3)
    bpy.types.Scene.intuitionRF_smooth_ratio = bpy.props.FloatProperty(name='Smooth ratio', default=1.4)
    
    # register object classes
    bpy.utils.register_class(OBJECT_PT_intuitionRFPanel)
    bpy.utils.register_class(IntuitionRF_ObjectProperties)
    bpy.types.Object.intuitionRF_properties = bpy.props.PointerProperty(type=IntuitionRF_ObjectProperties)


def unregister():
    bpy.utils.unregister_class(IntuitionRFPanel)
    bpy.utils.unregister_class(IntuitionRF)
    bpy.utils.unregister_class(IntuitionRF_OT_add_domain)
    bpy.utils.unregister_class(IntuitionRF_OT_add_default_lines)
    bpy.utils.unregister_class(IntuitionRF_OT_add_preview_lines)
    bpy.utils.unregister_class(SceneProperties)
    bpy.utils.unregister_class(IntuitionRF_OT_add_meshline_x)
    bpy.utils.unregister_class(IntuitionRF_OT_add_meshline_y)
    bpy.utils.unregister_class(IntuitionRF_OT_add_meshline_z)        
    del bpy.types.Scene.center_freq
    del bpy.types.Scene.cutoff_freq
    del bpy.types.Scene.intuitionRF_objects
    del bpy.types.Scene.intuitionRF_domain
    del bpy.types.Scene.intuitionRF_excitation_type
    del bpy.types.Scene.intuitionRF_unit
    del bpy.types.Scene.intuitionRF_lines
    del bpy.types.Scene.intuitionRF_previewlines
    del bpy.types.Scene.intuitionRF_smooth_max_res
    del bpy.types.Scene.intuitionRF_smooth_ratio
    
    # unregister object classes
    bpy.utils.unregister_class(OBJECT_PT_intuitionRFPanel)
    bpy.utils.unregister_class(IntuitionRF_ObjectProperties)
    
if __name__ == "__main__":
    register()
