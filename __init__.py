
bl_info = {
    "name": "Mirror Animation",
    "author": "JayReigns",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "VIEW3D > Right Click",
    "description": "Mirror Animation action",
    "category": "Animation"
}

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty


NEGATE_DATA_PATH_XAXIS = (
    ('location', 0),
    ('rotation_quaternion', 2),
    ('rotation_quaternion', 3),
    ('rotation_euler', 2),
    ('rotation_euler', 1), # armature space z axis is y
)

NEGATE_DATA_PATH_YAXIS = (
    ('location', 2), # in armature space y axis is z
    ('rotation_quaternion', 2),
    ('rotation_quaternion', 1),
    ('rotation_euler', 0),
    ('rotation_euler', 1), # armature space z axis is y
)


#########################################################################################
# Create Mirror Map
#########################################################################################


def difference(a, b):
    """Find difference in two strings to check if they are left and right"""
    import os
    common_prefix = os.path.commonprefix((a,b))
    common_suffix = os.path.commonprefix((a[::-1],b[::-1]))[::-1]
    
    # TODO: add checks incase of 'alc' and 'arc'
    #       check if difference is at start or end
    #       check if surrounds with punctuation or camelcase
    return a[len(common_prefix) : len(a)-len(common_suffix)], b[len(common_prefix) : len(b)-len(common_suffix)]

def lower_tuple(wl):
    return tuple(w.lower() for w in wl)

def create_mirror_map(names, patterns=None):
    
    mirror_map = {}

    if patterns == None:
        # Insert more default pattern if necessary
        patterns = (('l', 'r'), ('left', 'right'))
    
    # lower case and remove difference eg. remove 't' from 'Left', 'Right'
    patterns = tuple(lower_tuple(difference(*pattern)) for pattern in patterns)
    rpatterns = tuple(pattern[::-1] for pattern in patterns)

    for lname in names:
        for name in names:
            if lower_tuple(difference(lname, name)) in (*patterns, *rpatterns):
                rname = name
                mirror_map[lname] = rname
                break
    
    return mirror_map


#########################################################################################
# Mirror Action
#########################################################################################


def negate_fcurve(fcurve):
    for k in fcurve.keyframe_points:
        k.co[1] = -k.co[1]
        k.handle_left[1] = -k.handle_left[1]
        k.handle_right[1] = -k.handle_right[1]

def mirror_action(act, axis='X'):
    
    if not (act and act.fcurves):
        print("No Keyframes")
        return
    
    # create name map
    # strip attribute suffix eg. 'pose.bones["root"].location' -> 'pose.bones["root"]'
    bone_names = {fc.data_path.rsplit('.', 1)[0] for fc in act.fcurves if '.' in fc.data_path}
    mirror_map = create_mirror_map(bone_names)

    if axis == 'X':
        negate_data_path_tuples = NEGATE_DATA_PATH_XAXIS
    elif axis == 'Y':
        negate_data_path_tuples = NEGATE_DATA_PATH_YAXIS
    else:
        raise ValueError(f"Unsupported {axis=}")

    for fc in act.fcurves:
        data_path = fc.data_path
        array_index = fc.array_index

        # bone curves are 'pose.bones["root"].location'
        # objects curves are simply 'location'
        path, _dot, attribute = data_path.rpartition('.')
        
        # check if it is bone curve then flip data_path
        if path and (path in mirror_map):
            fc.data_path = "".join((mirror_map[path], _dot, attribute))
        
        if (attribute, array_index) in negate_data_path_tuples:
            negate_fcurve(fc)


#########################################################################################
# OPERATORS
#########################################################################################


class ANIM_OT_Mirror_Action(Operator):
    """Mirrors Currently assigned Action"""
    bl_idname = "aniim.mirror_action"
    bl_label = "Mirror Action"
    bl_options = {"REGISTER","UNDO"}

    axis : EnumProperty(
        name="Axis",
        description="Select mirror axis",
        default='X',
        items = (
            ('X', 'X', "X axis"),
            ('Y', 'Y', "Y axis"),
            ('XY', 'XY', "Both XY axes"),
            ('O', 'Original', "Original"),
        )
    )

    @classmethod
    def poll(cls, context):
        return context.active_object \
            # and context.active_object.animation_data \
            # and context.active_object.animation_data.action \
            # and context.active_object.animation_data.action.fcurves

    def execute(self, context):

        if not context.active_object.animation_data:
            self.report({"ERROR"}, "No Animation Data")
            return {'CANCELLED'}
        if not context.active_object.animation_data.action:
            self.report({"ERROR"}, "No Action assigned")
            return {'CANCELLED'}
        if not context.active_object.animation_data.action.fcurves:
            self.report({"ERROR"}, "No Keyframes")
            return {'CANCELLED'}
        
        if self.axis in ('X', 'Y'): 
            mirror_action(context.active_object.animation_data.action, axis=self.axis)
        if self.axis == 'XY':
            mirror_action(context.active_object.animation_data.action, axis='X')
            mirror_action(context.active_object.animation_data.action, axis='Y')
        # Skip 'O'; helps back and forth between poses
        
        self.report({"INFO"}, f"Action mirrorred on {self.axis}-axis!")
        return {'FINISHED'}


#########################################################################################
# REGISTER/UNREGISTER
#########################################################################################


classes = (
    ANIM_OT_Mirror_Action,
)

def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(ANIM_OT_Mirror_Action.bl_idname, icon='MOD_MIRROR')

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)
    bpy.types.VIEW3D_MT_pose_context_menu.append(menu_func)

def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.types.VIEW3D_MT_pose_context_menu.remove(menu_func)


if __name__ == "__main__":
    register()
