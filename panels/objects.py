import bpy 
import sys
import bmesh
import mathutils
from mathutils import geometry

from CSXCAD import CSXCAD
from openEMS import openEMS
from openEMS.physical_constants import *

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
    bl_label = "IntuitionRF"
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
    # register object classes
    bpy.utils.register_class(OBJECT_PT_intuitionRFPanel)
    bpy.utils.register_class(IntuitionRF_ObjectProperties)
    bpy.types.Object.intuitionRF_properties = bpy.props.PointerProperty(type=IntuitionRF_ObjectProperties)

def unregister():
    # unregister object classes
    bpy.utils.unregister_class(OBJECT_PT_intuitionRFPanel)
    bpy.utils.unregister_class(IntuitionRF_ObjectProperties)
