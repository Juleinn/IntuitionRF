import bpy
from bpy.types import Node, GeometryNode, NodeSocket
from bpy.props import FloatProperty, PointerProperty

class IRFPrimitiveSocket(NodeSocket):
    bl_idname = 'IRFPrimitiveSocketType'
    bl_label = 'IRF primitive'

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (0.6, 0.6, 0.2, 1.0)  # RGBA

class IRFGeometryToPrimitive(Node):
    bl_idname = "IRFGeometryToPrimitiveType"
    bl_label = "Geometry to Primitive"
    
    def init(self, context):
        self.inputs.new("NodeSocketGeometry", "Geometry")
        self.outputs.new(IRFPrimitiveSocket.bl_idname, "Primitive")

    def update(self):
        pass  # Logic to handle updates, e.g., when inputs change

    def process(self, inputs):
        pass
        
    def draw_buttons(self, context, layout):
        pass

    def draw_label(self):
        return "RF Simulation"

def draw_node_menu(self, context):
    layout = self.layout
    layout.operator('node.add_node', text="Geometry to Primitive").type = IRFGeometryToPrimitive.bl_idname

# Register the custom node
def register():
    # register sockets
    bpy.utils.register_class(IRFPrimitiveSocket)

    # register nodes
    bpy.utils.register_class(IRFGeometryToPrimitive)

    # register node menu
    bpy.types.NODE_MT_add.append(draw_node_menu)

def unregister():
    # unregister menu 
    bpy.types.NODE_MT_add.remove(draw_node_menu)

    # unregister node nodes
    bpy.utils.unregister_class(IRFGeometryToPrimitive)

    # unregister sockets
    bpy.utils.unregister_class(IRFPrimitiveSocket)

