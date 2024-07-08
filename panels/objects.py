import bpy 
import sys
import bmesh
import mathutils
from mathutils import geometry

from CSXCAD import CSXCAD
from openEMS import openEMS, ports
from openEMS.physical_constants import *

import os
sys.path.append(os.path.abspath('..'))
from .. operators import meshing

class IntuitionRF_ObjectProperties(bpy.types.PropertyGroup):
    object_type: bpy.props.EnumProperty(
        name = 'Type',
        description = 'Select an option', 
        items = [
            ('none', 'None', 'Ignored for computations'),
            ('metal', 'metal', 'metal'),
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
            ('x', 'x', 'x'),
            ('y', 'y', 'y'),
            ('z', 'z', 'z')
        ]
    )
    port_active: bpy.props.BoolProperty(name='Active', default=False)

    dump_type: bpy.props.EnumProperty(
        name = 'Dump Type',
        description = 'Dump Type', 
        items = [
            ("0", "E field/time", "E-field time-domain dump (default)"),
            ("1", "H field/time", "H-field time-domain dump"),
            ("2", "Current/time", "electric current time-domain dump"),
            ("3",  "Current density/time", "total current density (rot(H)) time-domain dump"),
            ("10", "E field/freq", " E-field frequency-domain dump"),
            ("11", "H field/freq", " H-field frequency-domain dump"),
            ("12", "Current/freq", " electric current frequency-domain dump"),
            ("13", "Current density/freq", " total current density (rot(H)) frequency-domain dump"),
            ("20", "local SAR/freq", " local SAR frequency-domain dump"),
            ("21", "1g avg. SAR/freq", " 1g averaging SAR frequency-domain dump"),
            ("22", "10g avg. SAR/freq", " 10g averaging SAR frequency-domain dump"),
            ("29", "raw SAR", " raw data needed for SAR calculations (electric field FD, cell volume, conductivity and density)")
        ]
    )

    dump_mode: bpy.props.EnumProperty(
        name = 'Dump Mode',
        description = 'Dump Mode', 
        items = [
            ("0", "no-interpolation", "no-interpolation"),
            ("1", "node-interpolation", "node-interpolation"),
            ("2", "cell-interpolation", "cell-interpolation")
        ]
    )

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
            if obj.name in meshing.ports.keys():
                row = layout.row()
                row.operator("intuitionrf.plot_port_return_loss")
                row.operator("intuitionrf.plot_port_impedance")

        if obj.intuitionRF_properties.object_type == "dumpbox":
            row = layout.row()
            row.prop(obj.intuitionRF_properties, "dump_type")
            row = layout.row()
            row.prop(obj.intuitionRF_properties, "dump_mode")



def register():
    # register object classes
    bpy.utils.register_class(OBJECT_PT_intuitionRFPanel)
    bpy.utils.register_class(IntuitionRF_ObjectProperties)
    bpy.types.Object.intuitionRF_properties = bpy.props.PointerProperty(type=IntuitionRF_ObjectProperties)

def unregister():
    # unregister object classes
    bpy.utils.unregister_class(OBJECT_PT_intuitionRFPanel)
    bpy.utils.unregister_class(IntuitionRF_ObjectProperties)
