bl_info = {
    "name": "IntuitionRF an OpenEMS wrapper for blender",
    "blender": (2, 80, 0),
    "category": "Object",
    "version": (0,3,0),
    "description": "A plugin for setting up OpenEMS simulations in Blender"
}
# bl_info = {"name": "My Test Addon", "category": "Object"}
#bl_info = {
#    "name": "My Addon",
#    "blender": (2, 80, 0),
#    "category": "Object",
#    "version": (1, 0, 0),
#    "location": "View3D > Add > Mesh > My Addon",
#    "description": "An example add-on",
#    "warning": "",
#    "wiki_url": "",
#    "tracker_url": "",
#    "support": "COMMUNITY",
#}

import sys
if __name__ == "__main__":
    # for release building
    if sys.argv[1] == "--version":
        v = bl_info["version"]
        print(f"{v[0]}.{v[1]}.{v[2]}")
        sys.exit(1)

# this is a horrible workaround to get multiprocessing to work on windows systems 
# by default forking with multiprocessing.Process (or multiprocessing.Pool) would cause the 
# whole init sequence to trigger for each process except import bpy would fail because it is 
# only accessible from a blender context, which is not needed under forked context because we are 
# only processing files (vtr to vdb). pyopenvdb, shipped with blender, is still required for this 
# to work without requiring yet another external dependency 
# TODO find a way to ignore import failures only in a forked context
# or find a proper way to import in forked context on windows
try:
    import bpy 
    import bmesh
    import mathutils
    from mathutils import geometry

    from bpy.types import Operator, AddonPreferences
    from bpy.props import StringProperty
    import subprocess

    import os


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

        openEMS_directory: StringProperty(
            name="openEMS directory (windows only)",
            default="",
            subtype='DIR_PATH'
        )

        def draw(self, context):
            layout = self.layout
            layout.label(text="Configure IntuitionRF to your openEMS install")
            layout.prop(self, "syspath")
            layout.operator(DetectSystem.bl_idname)
            layout.prop(self, "openEMS_directory")


    class OBJECT_OT_IntuitionRFPreferences(Operator):
        """IntuitionRF preferences oerator"""
        bl_idname = "object.addon_prefs_example"
        bl_label = "IntuitionRF system configuration"
        bl_options = {'REGISTER', 'UNDO'}

        def execute(self, context):
            return {'FINISHED'}

    # make variables for modules
    # so we can global import from within register function
    #meshing = None
    #scene = None
    #objects = None

    def register():
        global meshing
        global scene 
        global objects 
        global geometry_source

        bpy.utils.register_class(DetectSystem)
        bpy.utils.register_class(OBJECT_OT_IntuitionRFPreferences)
        bpy.utils.register_class(IntuitionRFAddonPreferences)

        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        if addon_prefs.syspath == "":
            print('Warning : syspath is empty. Skipping addon load')
            return

        import ast
        syspath = ast.literal_eval(addon_prefs.syspath)

        for item in syspath:
            sys.path.append(item)

        # import the dll path
        if sys.platform == "win32" and addon_prefs.openEMS_directory != "":
            os.add_dll_directory(addon_prefs.openEMS_directory)
        
        # print(sys.path)
        #
        if 'meshing' in globals(): #means Blender already started once
            import importlib
            # print("reimporting")
            importlib.reload(meshing)
            importlib.reload(scene)
            importlib.reload(objects)
            importlib.reload(geometry_source)
        else: #start up
            # print("First time importing")
            from . operators import meshing
            from . panels import scene, objects
            from . nodes import geometry_source

        # register operators
        meshing.register()

        # register panels
        scene.register()
        objects.register()

        geometry_source.register()

    def unregister():
        global objects 
        global scene 
        global meshing

        # unregister panels
        objects.unregister()
        scene.unregister()
        geometry_source.unregister()

        # unregister operators
        meshing.unregister()

        bpy.utils.unregister_class(DetectSystem)
        bpy.utils.unregister_class(OBJECT_OT_IntuitionRFPreferences)
        bpy.utils.unregister_class(IntuitionRFAddonPreferences)

    if __name__ == "__main__":
        register()
except:
    print("Failed to import bpy")
