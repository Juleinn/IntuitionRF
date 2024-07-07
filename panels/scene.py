import bpy 
import sys
import bmesh
import mathutils
from mathutils import geometry

from CSXCAD import CSXCAD
from openEMS import openEMS
from openEMS.physical_constants import *

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
        row = layout.row()
        row.operator("intuitionrf.preview_csx")
        row = layout.row()
        row.operator("intuitionrf.preview_pec_dump")

def register():
    bpy.utils.register_class(IntuitionRFPanel)
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
    bpy.types.Scene.intuitionRF_PEC_dump = bpy.props.PointerProperty(type=bpy.types.Object, name='lines')

def unregister():
    bpy.utils.unregister_class(IntuitionRFPanel)

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
    del bpy.types.Scene.intuitionRF_PEC_dump
