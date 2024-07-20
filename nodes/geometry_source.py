import bpy
from bpy.types import GeometryNodeCustomGroup, IDPropertyWrapPtr, Node, GeometryNode, NodeSocket, NodeTree, GeometryNodeTree, Point
from bpy.props import FloatProperty, PointerProperty, EnumProperty

class NodeSetPort(bpy.types.GeometryNodeCustomGroup):
    """Sets the port options by setting attributes on the points"""
    bl_idname = 'NodeSetPort'
    bl_label = 'Set Port'
    
    def init(self, context):
        # Create a new node tree for the custom group
        self.node_tree = bpy.data.node_groups.new('CustomAttributeNodeTree', 'GeometryNodeTree')
        
        # Create input and output nodes
        input_node = self.node_tree.nodes.new('NodeGroupInput')
        output_node = self.node_tree.nodes.new('NodeGroupOutput')
        
        # Add the Store Named Attribute node
        node_store_portindex = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_portindex.inputs['Name'].default_value = 'intuitionrf.port_index'
        node_store_portindex.data_type = 'INT'
        node_store_portindex.inputs['Value'].default_value = 1        

        # port impedance
        node_store_port_impedance = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_port_impedance.inputs['Name'].default_value = 'intuitionrf.port_impedance'
        node_store_port_impedance.data_type = 'FLOAT'
        node_store_port_impedance.inputs['Value'].default_value = 50.0        

        # port excitation axis
        node_store_port_axis = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_port_axis.inputs['Name'].default_value = 'intuitionrf.port_axis'
        node_store_port_axis.data_type = 'FLOAT_VECTOR'

        # port active
        node_store_port_active = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_port_active.inputs['Name'].default_value = 'intuitionrf.port_active'
        node_store_port_active.data_type = 'BOOLEAN'
        node_store_port_active.inputs['Value'].default_value = False

        # Create links
        self.node_tree.interface.new_socket("Geometry", description="Input geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        self.node_tree.interface.new_socket("Index", description="Index of port", in_out="INPUT", socket_type="NodeSocketInt")
        self.node_tree.interface.new_socket("Impedance (ohm)", description="Port Impedance (ohm)", in_out="INPUT", socket_type="NodeSocketFloat")
        self.node_tree.interface.new_socket("Axis", description="axis", in_out="INPUT", socket_type="NodeSocketVector")
        self.node_tree.interface.new_socket("Active", description="Active", in_out="INPUT", socket_type="NodeSocketBool")
        self.node_tree.interface.new_socket("Geometry", description="Output geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

        # inputs to the nodes
        self.node_tree.links.new(input_node.outputs[0], node_store_portindex.inputs[0])
        self.node_tree.links.new(input_node.outputs[1], node_store_portindex.inputs[3])
        self.node_tree.links.new(input_node.outputs[2], node_store_port_impedance.inputs[3])
        self.node_tree.links.new(input_node.outputs[3], node_store_port_axis.inputs[3])
        self.node_tree.links.new(input_node.outputs[4], node_store_port_active.inputs[3])

        # chain store attribute nodes
        self.node_tree.links.new(node_store_portindex.outputs[0], node_store_port_impedance.inputs[0])
        self.node_tree.links.new(node_store_port_impedance.outputs[0], node_store_port_axis.inputs[0])
        self.node_tree.links.new(node_store_port_axis.outputs[0], node_store_port_active.inputs[0])
        
        # back to output
        self.node_tree.links.new(node_store_port_active.outputs[0], output_node.inputs[0])

class NodeSetPEC(bpy.types.GeometryNodeCustomGroup):
    """Sets the given geometry as PEC. Can mark edges (will be added as curves) and faces 
       as volumes, or planes"""
    bl_idname = 'NodeSetPEC'
    bl_label = 'Set PEC'
    
    def init(self, context):
        # Create a new node tree for the custom group
        self.node_tree = bpy.data.node_groups.new('CustomAttributeNodeTree', 'GeometryNodeTree')
        
        # Create input and output nodes
        input_node = self.node_tree.nodes.new('NodeGroupInput')
        output_node = self.node_tree.nodes.new('NodeGroupOutput')
        
        # Add the Store Named Attribute node
        node_store_pecedge = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_pecedge.inputs['Name'].default_value = 'intuitionrf.pec_edge'
        node_store_pecedge.data_type = 'BOOLEAN'
        node_store_pecedge.inputs['Value'].default_value = True        
        node_store_pecedge.domain = 'EDGE'

        node_store_aa_faces = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_aa_faces.inputs['Name'].default_value = 'intuitionrf.pec_aa_face'
        node_store_aa_faces.data_type = 'BOOLEAN'
        node_store_aa_faces.inputs['Value'].default_value = True        
        node_store_aa_faces.domain = 'FACE'

        node_store_volume = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_volume.inputs['Name'].default_value = 'intuitionrf.pec_volume'
        node_store_volume.data_type = 'BOOLEAN'
        node_store_volume.inputs['Value'].default_value = True        
        node_store_volume.domain = 'FACE'

        # wiring in-out
        self.node_tree.interface.new_socket("Geometry", description="Input geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        self.node_tree.interface.new_socket("Geometry", description="Output geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        self.node_tree.interface.new_socket("PEC edge", description="PEC Edge", in_out="INPUT", socket_type="NodeSocketBool")
        self.node_tree.interface.new_socket("AA faces", description="AA faces", in_out="INPUT", socket_type="NodeSocketBool")
        self.node_tree.interface.new_socket("Volume", description="Volume", in_out="INPUT", socket_type="NodeSocketBool")

        # wire inputs
        self.node_tree.links.new(input_node.outputs[0], node_store_pecedge.inputs[0])
        self.node_tree.links.new(input_node.outputs[1], node_store_pecedge.inputs[3])
        self.node_tree.links.new(input_node.outputs[2], node_store_aa_faces.inputs[3])
        self.node_tree.links.new(input_node.outputs[3], node_store_volume.inputs[3])

        # chain link attribute node 
        self.node_tree.links.new(node_store_pecedge.outputs[0], node_store_aa_faces.inputs[0])
        self.node_tree.links.new(node_store_aa_faces.outputs[0], node_store_volume.inputs[0])

        # link to output
        self.node_tree.links.new(node_store_volume.outputs[0], output_node.inputs[0])

class NodeSetMaterial(bpy.types.GeometryNodeCustomGroup):
    """Marks the given geometry (face attributes) as a material with epsilon and optional kappa"""
    bl_idname = 'NodeSetMaterial'
    bl_label = 'Set Material'
    
    def init(self, context):
        # Create a new node tree for the custom group
        self.node_tree = bpy.data.node_groups.new('CustomAttributeNodeTree', 'GeometryNodeTree')
        
        # Create input and output nodes
        input_node = self.node_tree.nodes.new('NodeGroupInput')
        output_node = self.node_tree.nodes.new('NodeGroupOutput')

        # non-material vertices will have a epsilon value of 0 (impossible in the real world, where minimum is 1)
        node_store_material_epsilon = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_material_epsilon.inputs['Name'].default_value = 'intuitionrf.epsilonr'
        node_store_material_epsilon.data_type = 'FLOAT'
        node_store_material_epsilon.inputs['Value'].default_value = 1.0        
        node_store_material_epsilon.domain = 'FACE'

        node_store_material_use_kappa = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_material_use_kappa.inputs['Name'].default_value = 'intuitionrf.use_kappa'
        node_store_material_use_kappa.data_type = 'BOOLEAN'
        node_store_material_use_kappa.inputs['Value'].default_value = True
        node_store_material_use_kappa.domain = 'FACE'

        node_store_material_kappa = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_material_kappa.inputs['Name'].default_value = 'intuitionrf.kappa'
        node_store_material_kappa.data_type = 'FLOAT'
        node_store_material_kappa.inputs['Value'].default_value = True
        node_store_material_kappa.domain = 'FACE'

        self.node_tree.interface.new_socket("Geometry", description="Input geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        self.node_tree.interface.new_socket("Geometry", description="Output geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        self.node_tree.interface.new_socket("EpsilonR", description="EpsilonR", in_out="INPUT", socket_type="NodeSocketFloat")
        self.node_tree.interface.new_socket("Use Kappa", description="Use Kappa", in_out="INPUT", socket_type="NodeSocketBool")
        self.node_tree.interface.new_socket("Kappa", description="Kappa", in_out="INPUT", socket_type="NodeSocketFloat")

        # input 
        self.node_tree.links.new(input_node.outputs[0], node_store_material_epsilon.inputs[0])
        self.node_tree.links.new(input_node.outputs[1], node_store_material_epsilon.inputs[3])
        self.node_tree.links.new(input_node.outputs[2], node_store_material_use_kappa.inputs[3])
        self.node_tree.links.new(input_node.outputs[3], node_store_material_kappa.inputs[3])

        # chain attribute nodes
        self.node_tree.links.new(node_store_material_epsilon.outputs[0], node_store_material_use_kappa.inputs[0])
        self.node_tree.links.new(node_store_material_use_kappa.outputs[0], node_store_material_kappa.inputs[0])

        # output
        self.node_tree.links.new(node_store_material_kappa.outputs[0], output_node.inputs[0])

class NodeSetAnchor(bpy.types.GeometryNodeCustomGroup):
    """Marks the given geometry (vertices) as anchors for OpenEMS meshing"""
    bl_idname = 'NodeSetAnchor'
    bl_label = 'Set Anchor'
    
    def init(self, context):
        # Create a new node tree for the custom group
        self.node_tree = bpy.data.node_groups.new('CustomAttributeNodeTree', 'GeometryNodeTree')
        
        # Create input and output nodes
        input_node = self.node_tree.nodes.new('NodeGroupInput')
        output_node = self.node_tree.nodes.new('NodeGroupOutput')

        node_store_is_anchor = self.node_tree.nodes.new('GeometryNodeStoreNamedAttribute')
        node_store_is_anchor.inputs['Name'].default_value = 'intuitionrf.anchor'
        node_store_is_anchor.data_type = 'BOOLEAN'
        node_store_is_anchor.inputs['Value'].default_value = True

        # I/O
        self.node_tree.interface.new_socket("Geometry", description="Input geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        self.node_tree.interface.new_socket("Is anchor", description="Is anchor", in_out="INPUT", socket_type="NodeSocketBool")
        self.node_tree.interface.new_socket("Geometry", description="Output geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

        self.node_tree.links.new(input_node.outputs[0], node_store_is_anchor.inputs[0])
        self.node_tree.links.new(input_node.outputs[0], node_store_is_anchor.inputs[3])
        self.node_tree.links.new(node_store_is_anchor.outputs[0], output_node.inputs[0])


def draw_node_menu(self, context):
    layout = self.layout
    layout.operator('node.add_node', text="IntuitionRF port").type = NodeSetPort.bl_idname
    layout.operator('node.add_node', text="IntuitionRF PEC").type = NodeSetPEC.bl_idname
    layout.operator('node.add_node', text="IntuitionRF Material").type = NodeSetMaterial.bl_idname
    layout.operator('node.add_node', text="IntuitionRF Anchor").type = NodeSetAnchor.bl_idname

# Register the custom node
def register():
    print('register nodes')
    # register sockets
    # bpy.utils.register_class(IRFPrimitiveSocket)

    # register nodes
    bpy.utils.register_class(NodeSetPort)
    bpy.utils.register_class(NodeSetPEC)
    bpy.utils.register_class(NodeSetMaterial)
    bpy.utils.register_class(NodeSetAnchor)

    # register node menu
    bpy.types.NODE_MT_add.append(draw_node_menu)

def unregister():
    # unregister menu 
    bpy.types.NODE_MT_add.remove(draw_node_menu)

    # unregister node nodes
    bpy.utils.unregister_class(NodeSetPort)
    bpy.utils.unregister_class(NodeSetPEC)
    bpy.utils.unregister_class(NodeSetMaterial)
    bpy.utils.unregister_class(NodeSetAnchor)

    # unregister sockets
    # bpy.utils.unregister_class(IRFPrimitiveSocket)
