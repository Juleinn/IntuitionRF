import bpy
from bpy.types import GeometryNodeCustomGroup, Node, GeometryNode, NodeSocket, NodeTree, GeometryNodeTree
from bpy.props import FloatProperty, PointerProperty, EnumProperty

import IPython

class IRFPrimitiveSocket(NodeSocket):
    bl_idname = 'IRFPrimitiveSocketType'
    bl_label = 'IRF primitive'

    some_prop: FloatProperty(name='some_float', description='a float')

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (1.00, 0.655, 0.0600, 1.0)

class IRFGeometryToPrimitive(GeometryNode):
    bl_idname = "IRFGeometryToPrimitiveType"
    bl_label = "Object to Primitive"

    object_type: bpy.props.EnumProperty(
        name = 'Type',
        description = 'Select an option', 
        items = [
            ('none', 'None', 'Ignored for computations'),
            ('metal_volume', 'metal (Volume)', 'metal (Volume)'),
            ('metal_aa_faces', 'metal (AA faces)', 'metal (AA faces)'),
            ('material', 'material (\u03B5,\u03BA)', 'material defined by \u03B5 and \u03BA'),
            ('dumpbox', 'Dump Box', 'Dump box for E or H fields (to be specified)'),
            ('nf2ff', 'NF2FF Box', 'Near Field to Far Field computation box'),
            ('port', 'Port', 'Excitation Port'),
        ],
        # force redraw/update on change
        update = lambda self, context: self.update()
    )

    target: bpy.props.PointerProperty(
        type=bpy.types.Object, 
        name='target',
        # force redraw/update on change
        update = lambda self, context: self.update()
    )
    
    def draw_buttons(self, context, layout):
        layout.row()
        layout.prop(self, "target")
        layout.prop(self, "object_type")

    def init(self, context):
        self.outputs.new(IRFPrimitiveSocket.bl_idname, "Primitive")

    def update(self):
        # copy property into the socket
        self.outputs[0].object_type = self.object_type
        self.outputs[0].target = self.target

    def draw_label(self):
        return "Object to primitive"

class IRFSimulationTree(NodeTree):
    bl_idname = "IRFSimulationTree"
    bl_label = "IRF Simulation tree"
    bl_icon = "NODE"

class IRFSimulation(GeometryNodeCustomGroup):
    bl_idname = "GeometryNodeTree"
    bl_label = "Simulation"

    @classmethod
    def poll(cls, context):  # mandatory with geonode
        return True

    def init(self, context):
        # example
        group = bpy.data.node_groups.new("group_name", type='GeometryNodeTree')
        nodes = group.nodes
        input_node= nodes.new(type='NodeGroupInput')
        #math_node = nodes.new(type='ShaderNodeMath')
        Input_1 = group.interface.new_socket(name='Input Name', in_out='INPUT', socket_type='NodeSocketFloat')
        self.node_tree = group
        IPython.embed(colors='neutral')


    #def get_inputs_by_type(self, target_type):
    #    # return a filtered list of inputs by type
    #    return list(filter(lambda input: type(input) == target_type, self.inputs))

    #def get_last_input_by_type(self, target_type):
    #    # let it crash if len is 0 cause it should never be the case
    #    inputs = self.get_inputs_by_type(target_type)
    #    return inputs[len(inputs) - 1]

    #def draw_buttons(self, context, layout):
    #    pass
        #for prop in self.bl_rna.properties:
        #    if prop.is_runtime and not prop.is_readonly:
        #        text = "" if prop.type == "ENUM" else prop.name
        #        layout.prop(self, prop.identifier, text=text)


    #def update_inputs(self):
    #    # always exclude the update on init
    #    if len(self.inputs) == 0:
    #        return

    #    # remove unused inputs
    #    last_input = self.get_last_input_by_type(IRFPrimitiveSocket)
    #    while not last_input.is_linked and len(self.get_inputs_by_type(IRFPrimitiveSocket)) > 1:
    #        if not last_input.is_linked:
    #            self.inputs.remove(last_input)
    #        last_input = self.get_last_input_by_type(IRFPrimitiveSocket)

    #    # add inputs as needed
    #    last_input = self.get_last_input_by_type(IRFPrimitiveSocket)
    #    if last_input.is_linked:
    #        self.inputs.new(IRFPrimitiveSocket.bl_idname, "Primitive")


    #def get_primitives(self):
    #    sockets = self.get_inputs_by_type(IRFPrimitiveSocket)
    #    for socket in sockets:
    #        if socket.is_linked:
    #            print('found a linked socket')
    #            # get the output socket from the connected node 
    #            link = socket.links[0] # this is not a multilink socket
    #            output_socket = link.from_node.outputs[link.from_socket.name]


    #def update(self):
    #    print('updated called on SIM')

        # primitives = self.get_primitives()



        #if self.inputs[1].is_linked:
        #    print('input 1 linked')
        #    input_link = self.inputs[1].links[0]
        #    input_node = input_link.from_node
        #    output_socket = input_node.outputs[input_link.from_socket.name]
        #    
        #    print(output_socket.some_prop)
        #    print(f"arbitrary prop : {output_socket['another_prop']}")
        #else:
        #    print('input 1 not linked')


    def draw_label(self):
        return "RF Simulation"

class CustomNode(Node):
    bl_idname = 'CustomNode'
    bl_label = 'Custom Node'

    value_from_value_node: FloatProperty(
        name="Value from Value Node",
        default=0.0
    )

    def init(self, context):
        self.inputs.new('NodeSocketFloat', "Value Input")
        self.outputs.new('NodeSocketFloat', "Output")

    def update(self):
        print('update custom')

    def execute(self, context):
        if self.inputs['Value Input'].is_linked:
            # Retrieve the value from the connected Value node
            self.value_from_value_node = self.inputs['Value Input'].links[0].from_socket.default_value
        else:
            # Fallback if no node is connected
            self.value_from_value_node = 0.0
        
        # Perform any other operations based on the value if needed
        output_value = self.value_from_value_node * 2  # Example operation

        # Update the output socket
        self.outputs['Output'].default_value = output_value

def draw_node_menu(self, context):
    layout = self.layout
    layout.operator('node.add_node', text="Geometry to Primitive").type = IRFGeometryToPrimitive.bl_idname
    layout.operator('node.add_node', text="IRF - Simulation").type = IRFSimulation.bl_idname
    layout.operator('node.add_node', text="IRF - CustomNode").type = CustomNode.bl_idname

# Register the custom node
def register():
    # register sockets
    bpy.utils.register_class(IRFPrimitiveSocket)

    # register node trees
    bpy.utils.register_class(IRFSimulationTree)

    # register nodes
    bpy.utils.register_class(IRFGeometryToPrimitive)
    bpy.utils.register_class(IRFSimulation)
    bpy.utils.register_class(CustomNode)

    # register node menu
    bpy.types.NODE_MT_add.append(draw_node_menu)

def unregister():
    # unregister menu 
    bpy.types.NODE_MT_add.remove(draw_node_menu)

    # unregister node nodes
    bpy.utils.unregister_class(IRFGeometryToPrimitive)
    bpy.utils.unregister_class(IRFSimulation)
    bpy.utils.unregister_class(CustomNode)

    # unregister node trees 
    bpy.utils.unregister_class(IRFSimulationTree)

    # unregister sockets
    bpy.utils.unregister_class(IRFPrimitiveSocket)
