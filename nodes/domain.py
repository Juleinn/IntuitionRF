import bpy
from bpy.types import Node, GeometryNode, NodeSocket
from bpy.props import FloatProperty, PointerProperty

import IPython

class IRFPrimitiveSocket(NodeSocket):
    bl_idname = 'IRFPrimitiveSocketType'
    bl_label = 'IRF primitive'

    some_prop: FloatProperty(name='some_float', description='a float')

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (1.00, 0.655, 0.0600, 1.0)

class IRFGeometryToPrimitive(Node):
    bl_idname = "IRFGeometryToPrimitiveType"
    bl_label = "Geometry to Primitive"
    
    def init(self, context):
        self.inputs.new("NodeSocketGeometry", "Geometry")
        self.outputs.new(IRFPrimitiveSocket.bl_idname, "Primitive")

    def update(self):
        print('Geo To primitive update')
        self.outputs[0].some_prop = 42
        self.outputs[0]['another_prop']= 42
        print(f"source = {self.outputs[0].some_prop}")

    def draw_label(self):
        return "Geometry to Primitive"

class IRFSimulation(Node):
    bl_idname = "IRFSimulationType"
    bl_label = "Simulation"

    def init(self, context):
        self.inputs.new("NodeSocketGeometry", "Geometry")
        self.inputs.new(IRFPrimitiveSocket.bl_idname, "Primitive")

    def get_inputs_by_type(self, target_type):
        # return a filtered list of inputs by type
        return list(filter(lambda input: type(input) == target_type, self.inputs))

    def get_last_input_by_type(self, target_type):
        # let it crash if len is 0 cause it should never be the case
        inputs = self.get_inputs_by_type(target_type)
        return inputs[len(inputs) - 1]

    def update_inputs(self):
        # always exclude the update on init
        if len(self.inputs) == 0:
            return

        # remove unused inputs
        last_input = self.get_last_input_by_type(IRFPrimitiveSocket)
        while not last_input.is_linked and len(self.get_inputs_by_type(IRFPrimitiveSocket)) > 1:
            if not last_input.is_linked:
                self.inputs.remove(last_input)
            last_input = self.get_last_input_by_type(IRFPrimitiveSocket)

        # add inputs as needed
        last_input = self.get_last_input_by_type(IRFPrimitiveSocket)
        if last_input.is_linked:
            self.inputs.new(IRFPrimitiveSocket.bl_idname, "Primitive")

    def update(self):
        self.update_inputs()
        print(type(self.inputs))

        if self.inputs[1].is_linked:
            print('input 1 linked')
            input_link = self.inputs[1].links[0]
            input_node = input_link.from_node
            output_socket = input_node.outputs[input_link.from_socket.name]
            
            print(output_socket.some_prop)
            print(f"arbitrary prop : {output_socket['another_prop']}")
        else:
            print('input 1 not linked')

    def draw_label(self):
        return "RF Simulation"

def draw_node_menu(self, context):
    layout = self.layout
    layout.operator('node.add_node', text="Geometry to Primitive").type = IRFGeometryToPrimitive.bl_idname
    layout.operator('node.add_node', text="IRF - Simulation").type = IRFSimulation.bl_idname

# Register the custom node
def register():
    # register sockets
    bpy.utils.register_class(IRFPrimitiveSocket)

    # register nodes
    bpy.utils.register_class(IRFGeometryToPrimitive)
    bpy.utils.register_class(IRFSimulation)
    # register node menu
    bpy.types.NODE_MT_add.append(draw_node_menu)

def unregister():
    # unregister menu 
    bpy.types.NODE_MT_add.remove(draw_node_menu)

    # unregister node nodes
    bpy.utils.unregister_class(IRFGeometryToPrimitive)
    bpy.utils.unregister_class(IRFSimulation)

    # unregister sockets
    bpy.utils.unregister_class(IRFPrimitiveSocket)
