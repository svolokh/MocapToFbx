import bpy
import io_anim_bvh.import_bvh
import io_scene_fbx.export_fbx_bin
import bpy_extras.io_utils
import sys

class FakeOperator:
    def report():
        pass

bvh_in = sys.argv[4]
fbx_out = sys.argv[5]

# remove any existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(confirm=False)

gm = bpy_extras.io_utils.axis_conversion(from_forward='-Z', from_up='Y')
io_anim_bvh.import_bvh.load(bpy.context, bvh_in, global_matrix=gm.to_4x4())

io_scene_fbx.export_fbx_bin.save_single(FakeOperator(), 
        bpy.context.scene, 
        bpy.context.scene.view_layers[0].depsgraph, 
        filepath=fbx_out, 
        context_objects=bpy.context.view_layer.objects,
        axis_up='Y',
        axis_forward='-Z')

exit(0)
