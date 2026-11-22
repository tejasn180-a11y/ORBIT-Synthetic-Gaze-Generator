import bpy, math
from pathlib import Path
from mathutils import Euler
from bpy_extras.object_utils import world_to_camera_view
class EyesController:
    def __init__(self,root,max_horizontal_deg=22,max_vertical_deg=18):
        self.root=Path(root); self.renders=self.root/"renders"; self.renders.mkdir(parents=True,exist_ok=True)
        self.scene=bpy.context.scene; self.camera=bpy.data.objects["VirtualCamera_FIXED_40cm"]
        self.pivots={s:bpy.data.objects["EyePivot_"+s] for s in ("L","R")}
        self.pupils={s:bpy.data.objects["Pupil_"+s] for s in ("L","R")}
        self.mh=math.radians(max_horizontal_deg); self.mv=math.radians(max_vertical_deg); self.reset()
    def move(self,h,v):
        h=max(-1,min(1,float(h))); v=max(-1,min(1,float(v)))
        for p in self.pivots.values():p.rotation_euler=Euler((-v*self.mv,0,h*self.mh),"XYZ")
        bpy.context.view_layer.update()
    def reset(self):
        for p in self.pivots.values():p.rotation_euler=Euler((0,0,0),"XYZ")
        bpy.context.view_layer.update()
    def pupil_pixels(self):
        bpy.context.view_layer.update(); w=self.scene.render.resolution_x; h=self.scene.render.resolution_y; out={}
        for s,p in self.pupils.items():
            n=world_to_camera_view(self.scene,self.camera,p.matrix_world.translation)
            out[s]=[round(n.x*w,3),round((1-n.y)*h,3)]
        return out
    def render(self,k,theta,h,v):
        self.scene.render.filepath=str(self.renders/f"frame_{k:02d}.png"); bpy.ops.render.render(write_still=True)
        pp=self.pupil_pixels(); rot={s:[round(math.degrees(float(a)),5) for a in p.rotation_euler] for s,p in self.pivots.items()}
        dg=bpy.context.evaluated_depsgraph_get()
        m=self.camera.calc_matrix_camera(dg,x=self.scene.render.resolution_x,y=self.scene.render.resolution_y,scale_x=1,scale_y=1)
        return {"frame":k,"theta_rad":round(theta,8),"input":{"h":round(h,8),"v":round(v,8)},
          "eye_rotation_L_deg":rot["L"],"eye_rotation_R_deg":rot["R"],
          "pupil_center_2D_L_px":pp["L"],"pupil_center_2D_R_px":pp["R"],
          "pupil_center_2D_L_normalized":[round(pp["L"][0]/self.scene.render.resolution_x,8),round(pp["L"][1]/self.scene.render.resolution_y,8)],
          "pupil_center_2D_R_normalized":[round(pp["R"][0]/self.scene.render.resolution_x,8),round(pp["R"][1]/self.scene.render.resolution_y,8)],
          "camera_matrix":[[round(float(m[r][c]),8) for c in range(4)] for r in range(4)],
          "camera_world_matrix_4x4":[[round(float(self.camera.matrix_world[r][c]),8) for c in range(4)] for r in range(4)],
          "image":f"renders/frame_{k:02d}.png","resolution":[self.scene.render.resolution_x,self.scene.render.resolution_y],
          "coordinate_convention":"top-left pixel origin; +x right; +y down; h>0 right; v>0 up"}
