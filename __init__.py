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

from CSXCAD import CSXCAD
from openEMS import openEMS
from openEMS.physical_constants import *

if "meshing" in locals(): #means Blender already started once
    import importlib
    print("reimporting")
    importlib.reload(meshing)
    importlib.reload(scene)
    importlib.reload(objects)
else: #start up
    print("First time importing")
    from . operators import meshing
    from . panels import scene, objects

from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty
import subprocess

# need to setup the syspath proprties and operators before loading the rest of the plugin

class DetectSystem(Operator):
    """Detect System (syspath of system python)"""
    bl_idname = f"addon_prefs_example.detect_system"
    bl_label = f"Detect System"

    def execute(self, context):
        cmd = 'python3 -c "import sys; print(sys.path)"'
        
        addon_prefs = context.preferences.addons[__name__].preferences
        
        p = subprocess.Popen(cmd,
                     shell=True,
                     bufsize=1024,
                     stdin=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdout=subprocess.PIPE)

        for line in p.stdout:
            p.stdout.flush()

            addon_prefs.syspath = line.decode('utf8')

        return {'FINISHED'}

class IntuitionRFAddonPreferences(AddonPreferences):
    bl_idname = __name__

    syspath: StringProperty(
        name="System python's syspath",
        default=""
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Configure IntuitionRF to your openEMS install")
        layout.prop(self, "syspath")
        layout.operator(DetectSystem.bl_idname)


class OBJECT_OT_IntuitionRFPreferences(Operator):
    """IntuitionRF preferences oerator"""
    bl_idname = "object.addon_prefs_example"
    bl_label = "IntuitionRF system configuration"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

#syspath = ['', '/home/anton/code/python/libs', '/usr/local/lib/python311.zip', '/usr/local/lib/python3.11', '/usr/local/lib/python3.11/lib-dynload', '/home/anton/.local/lib/python3.11/site-packages', '/home/anton/.local/lib/python3.11/site-packages/CSXCAD-0.6.2-py3.11-linux-x86_64.egg', '/home/anton/.local/lib/python3.11/site-packages/openEMS-0.0.36-py3.11-linux-x86_64.egg', '/usr/local/lib/python3.11/site-packages']
#for item in syspath:
#    sys.path.append(item)
        
def register():
    bpy.utils.register_class(DetectSystem)
    bpy.utils.register_class(OBJECT_OT_IntuitionRFPreferences)
    bpy.utils.register_class(IntuitionRFAddonPreferences)

    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    if addon_prefs.syspath == "":
        return

    for item in addon_prefs.syspath:
        sys.path.append(item)
    # register operators
    meshing.register()

    # register panels
    scene.register()
    objects.register()

def unregister():
    # unregister operators
    meshing.unregister()
    
    # unregister panels
    scene.unregister()
    objects.unregister()

    bpy.utils.unregister_class(DetectSystem)
    bpy.utils.unregister_class(OBJECT_OT_IntuitionRFPreferences)
    bpy.utils.unregister_class(IntuitionRFAddonPreferences)

if __name__ == "__main__":
    register()
