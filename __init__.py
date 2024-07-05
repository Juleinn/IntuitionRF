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

if "bpy" in locals(): #means Blender already started once
    import importlib
    print("reimporting")
    print(str(meshing))
    importlib.reload(meshing)
    importlib.reload(scene)
    importlib.reload(objects)
else: #start up
    print("First time importing")
    from . operators import meshing
    from . panels import scene, objects

syspath = ['', '/home/anton/code/python/libs', '/usr/local/lib/python311.zip', '/usr/local/lib/python3.11', '/usr/local/lib/python3.11/lib-dynload', '/home/anton/.local/lib/python3.11/site-packages', '/home/anton/.local/lib/python3.11/site-packages/CSXCAD-0.6.2-py3.11-linux-x86_64.egg', '/home/anton/.local/lib/python3.11/site-packages/openEMS-0.0.36-py3.11-linux-x86_64.egg', '/usr/local/lib/python3.11/site-packages']
for item in syspath:
    sys.path.append(item)
        
def register():
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

if __name__ == "__main__":
    register()
