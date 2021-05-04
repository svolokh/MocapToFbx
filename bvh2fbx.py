import bpy
import os
import io_anim_bvh.import_bvh
import io_scene_fbx.export_fbx_bin
import bpy_extras.io_utils
import sys
import struct

from io_scene_fbx.export_fbx_bin import *

class FakeOperator:
    def report():
        pass

# copied from io_scene_fbx.export_fbx_bin to customize the output
def save_single(operator, scene, depsgraph, filepath="",
                global_matrix=Matrix(),
                apply_unit_scale=False,
                global_scale=1.0,
                apply_scale_options='FBX_SCALE_NONE',
                axis_up="Z",
                axis_forward="Y",
                context_objects=None,
                object_types=None,
                use_mesh_modifiers=True,
                use_mesh_modifiers_render=True,
                mesh_smooth_type='FACE',
                use_subsurf=False,
                use_armature_deform_only=False,
                bake_anim=True,
                bake_anim_use_all_bones=True,
                bake_anim_use_nla_strips=True,
                bake_anim_use_all_actions=True,
                bake_anim_step=1.0,
                bake_anim_simplify_factor=1.0,
                bake_anim_force_startend_keying=True,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_metadata=True,
                path_mode='AUTO',
                use_mesh_edges=True,
                use_tspace=True,
                embed_textures=False,
                use_custom_props=False,
                bake_space_transform=False,
                armature_nodetype='NULL',
                **kwargs
                ):

    # Clear cached ObjectWrappers (just in case...).
    ObjectWrapper.cache_clear()

    if object_types is None:
        object_types = {'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'}

    if 'OTHER' in object_types:
        object_types |= BLENDER_OTHER_OBJECT_TYPES

    # Default Blender unit is equivalent to meter, while FBX one is centimeter...
    unit_scale = units_blender_to_fbx_factor(scene) if apply_unit_scale else 100.0
    if apply_scale_options == 'FBX_SCALE_NONE':
        global_matrix = Matrix.Scale(unit_scale * global_scale, 4) @ global_matrix
        unit_scale = 1.0
    elif apply_scale_options == 'FBX_SCALE_UNITS':
        global_matrix = Matrix.Scale(global_scale, 4) @ global_matrix
    elif apply_scale_options == 'FBX_SCALE_CUSTOM':
        global_matrix = Matrix.Scale(unit_scale, 4) @ global_matrix
        unit_scale = global_scale
    else: # if apply_scale_options == 'FBX_SCALE_ALL':
        unit_scale = global_scale * unit_scale

    global_scale = global_matrix.median_scale
    global_matrix_inv = global_matrix.inverted()
    # For transforming mesh normals.
    global_matrix_inv_transposed = global_matrix_inv.transposed()

    # Only embed textures in COPY mode!
    if embed_textures and path_mode != 'COPY':
        embed_textures = False

    # Calculate bone correction matrix
    bone_correction_matrix = None  # Default is None = no change
    bone_correction_matrix_inv = None
    if (primary_bone_axis, secondary_bone_axis) != ('Y', 'X'):
        from bpy_extras.io_utils import axis_conversion
        bone_correction_matrix = axis_conversion(from_forward=secondary_bone_axis,
                                                 from_up=primary_bone_axis,
                                                 to_forward='X',
                                                 to_up='Y',
                                                 ).to_4x4()
        bone_correction_matrix_inv = bone_correction_matrix.inverted()


    media_settings = FBXExportSettingsMedia(
        path_mode,
        os.path.dirname(bpy.data.filepath),  # base_src
        os.path.dirname(filepath),  # base_dst
        # Local dir where to put images (media), using FBX conventions.
        os.path.splitext(os.path.basename(filepath))[0] + ".fbm",  # subdir
        embed_textures,
        set(),  # copy_set
        set(),  # embedded_set
    )

    settings = FBXExportSettings(
        operator.report, (axis_up, axis_forward), global_matrix, global_scale, apply_unit_scale, unit_scale,
        bake_space_transform, global_matrix_inv, global_matrix_inv_transposed,
        context_objects, object_types, use_mesh_modifiers, use_mesh_modifiers_render,
        mesh_smooth_type, use_subsurf, use_mesh_edges, use_tspace,
        armature_nodetype, use_armature_deform_only,
        add_leaf_bones, bone_correction_matrix, bone_correction_matrix_inv,
        bake_anim, bake_anim_use_all_bones, bake_anim_use_nla_strips, bake_anim_use_all_actions,
        bake_anim_step, bake_anim_simplify_factor, bake_anim_force_startend_keying,
        False, media_settings, use_custom_props,
    )

    import bpy_extras.io_utils

    print('\nFBX export starting... %r' % filepath)
    start_time = time.process_time()

    # Generate some data about exported scene...
    scene_data = fbx_data_from_scene(scene, depsgraph, settings)

    root = elem_empty(None, b"")  # Root element has no id, as it is not saved per se!

    # Mostly FBXHeaderExtension and GlobalSettings.
    fbx_header_elements(root, scene_data)

    # Documents and References are pretty much void currently.
    fbx_documents_elements(root, scene_data)
    fbx_references_elements(root, scene_data)

    # Templates definitions.
    fbx_definitions_elements(root, scene_data)

    # Actual data.
    fbx_objects_elements(root, scene_data)

    # How data are inter-connected.
    fbx_connections_elements(root, scene_data)

    # Animation.
    fbx_takes_elements(root, scene_data)

    # Cleanup!
    fbx_scene_data_cleanup(scene_data)

    # Apply some fixups specific to bvh to fbx conversion
    for objElem in root.elems:
        if objElem.id == b'Objects':
            for elem in objElem.elems:
                if elem.id == b'Model':
                    if elem.props[2].endswith(b'Null'):
                        props70 = elem.elems[1]
                        props70.elems = props70.elems[:1]
                elif elem.id == b'NodeAttribute':
                    if elem.props[1].find(b'_end') >= 0:
                        props70 = elem.elems[1]
                        for e in props70.elems:
                            if e.id == b'P' and e.props[0].endswith(b'Size'):
                                e.props[4] = struct.pack('d', 1.6)
            break

    # And we are down, we can write the whole thing!
    encode_bin.write(filepath, root, FBX_VERSION)

    # Clear cached ObjectWrappers!
    ObjectWrapper.cache_clear()

    # copy all collected files, if we did not embed them.
    if not media_settings.embed_textures:
        bpy_extras.io_utils.path_reference_copy(media_settings.copy_set)

    print('export finished in %.4f sec.' % (time.process_time() - start_time))
    return {'FINISHED'}


bvh_in = os.environ['BVH_IN']
fbx_out = os.environ['FBX_OUT'] 

# remove any existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(confirm=False)

gm = bpy_extras.io_utils.axis_conversion(from_forward='-Z', from_up='Y')
io_anim_bvh.import_bvh.load(bpy.context, bvh_in, global_matrix=gm.to_4x4())

save_single(FakeOperator(), 
        bpy.context.scene, 
        bpy.context.scene.view_layers[0].depsgraph, 
        filepath=fbx_out, 
        context_objects=bpy.context.view_layer.objects,
        add_leaf_bones=True,
        axis_up='Y',
        axis_forward='-Z')

exit(0)
