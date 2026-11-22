 
 
import bpy, math, json, importlib.util, zipfile
from pathlib import Path
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

OUT=Path.home()/"ORBIT_SyntheticEye_Project"/"Submission"
TEAM="ORBIT_Solo"
SIZE=1024
MAX_H,MAX_V=22.0,18.0

def mat(n,c,r=.45):
    m=bpy.data.materials.new(n); m.diffuse_color=(*c,1); m.use_nodes=True
    b=m.node_tree.nodes.get("Principled BSDF")
    if b: b.inputs["Base Color"].default_value=(*c,1); b.inputs["Roughness"].default_value=r
    return m

def ball(n,loc,scale,m,seg=48,rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,radius=1,location=loc)
    o=bpy.context.object; o.name=n; o.scale=scale
    if m:o.data.materials.append(m)
    for p in o.data.polygons:p.use_smooth=True
    return o

def line(n,pts,bevel,m):
    c=bpy.data.curves.new(n,'CURVE'); c.dimensions='3D'; c.bevel_depth=bevel; c.bevel_resolution=4
    s=c.splines.new('POLY'); s.points.add(len(pts)-1)
    for p,v in zip(s.points,pts):p.co=(*v,1)
    o=bpy.data.objects.new(n,c); bpy.context.collection.objects.link(o); o.data.materials.append(m)

def build():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    skin=mat("Skin",(0.48,.27,.19),.58); hi=mat("Skin_Highlight",(.62,.38,.29),.62)
    white=mat("Sclera",(.88,.91,.92),.22); iris=mat("Iris_Teal",(.025,.24,.28),.28)
    black=mat("Pupil_Black",(.003,.005,.008),.12); dark=mat("Socket_Shadow",(.12,.055,.045),.7)
    brow=mat("Eyebrow",(.10,.045,.035),.8); lip=mat("Lip",(.30,.09,.09),.55)
    ball("Face_Head_Mesh",(0,0,0),(.15,.105,.19),skin,64,48)
    ball("Chin",(0,-.075,-.115),(.075,.035,.045),hi)
    ball("Nose_Bridge",(0,-.105,-.005),(.023,.035,.070),hi)
    ball("Nose_Tip",(0,-.132,-.045),(.027,.022,.022),skin)
    ball("Nostril_L",(-.016,-.143,-.055),(.006,.004,.004),dark,24,16)
    ball("Nostril_R",(.016,-.143,-.055),(.006,.004,.004),dark,24,16)
    line("Mouth",[(-.045,-.108,-.105),(-.023,-.116,-.111),(0,-.118,-.113),(.023,-.116,-.111),(.045,-.108,-.105)],.003,lip)
    centers={"L":(-.052,-.094,.038),"R":(.052,-.094,.038)}
    for s,(x,y,z) in centers.items():
        bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=12,location=(x,y-.004,z),major_radius=.037,minor_radius=.0035,rotation=(math.radians(90),0,0))
        ring=bpy.context.object; ring.name="EyeSocket_"+s; ring.data.materials.append(dark)
        for p in ring.data.polygons:p.use_smooth=True
        line("Brow_"+s,[(x-.037,y-.01,z+.047),(x-.018,y-.018,z+.058),(x+.012,y-.018,z+.06),(x+.037,y-.01,z+.048)],.005,brow)
        pivot=bpy.data.objects.new("EyePivot_"+s,None); bpy.context.collection.objects.link(pivot)
        pivot.location=(x,y,z); pivot.empty_display_type='SPHERE'; pivot.empty_display_size=.008
        for child in [ball("Eyeball_"+s,(x,y,z),(.034,.028,.027),white),
                      ball("Iris_"+s,(x,y-.026,z),(.014,.006,.014),iris),
                      ball("Pupil_"+s,(x,y-.031,z),(.0065,.0035,.0065),black)]:
            child.parent=pivot; child.matrix_parent_inverse=pivot.matrix_world.inverted()
    mid=(centers["L"][1]+centers["R"][1])/2
    bpy.ops.object.camera_add(location=(0,mid-.40,.038)); cam=bpy.context.object; cam.name="VirtualCamera_FIXED_40cm"
    cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=50; cam.data.sensor_width=36; cam.data.sensor_fit='HORIZONTAL'; bpy.context.scene.camera=cam
    cam["distance_from_eye_midpoint_m"]=.40
    target=bpy.data.objects.new("Fixation_Target_35cm",None); bpy.context.collection.objects.link(target)
    target.location=(0,mid-.35,.038); target.empty_display_type='CIRCLE'; target.hide_render=True
    target["distance_from_eye_midpoint_m"]=.35
    for n,loc,power,size in [("Key_Light",(-.25,-.30,.28),18,.28),("Fill_Light",(.22,-.20,.05),7,.22)]:
        bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.name=n; l.data.energy=power; l.data.size=size
        l.rotation_euler=(Vector((0,0,0))-l.location).to_track_quat('-Z','Y').to_euler()
    w=bpy.data.worlds.new("Studio_World") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world=w; w.use_nodes=True
    w.node_tree.nodes["Background"].inputs["Color"].default_value=(.025,.035,.055,1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value=.28
    sc=bpy.context.scene
    try:sc.render.engine='BLENDER_EEVEE_NEXT'
    except:sc.render.engine='BLENDER_EEVEE'
    sc.render.resolution_x=sc.render.resolution_y=SIZE; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'
    sc.view_settings.view_transform='Standard'; cam.data.dof.use_dof=False
    return cam

WRAPPER=r'''import bpy, math
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
'''

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for f in ("wrapper","renders","demo"):(OUT/f).mkdir(exist_ok=True)
    for p in (OUT/"renders").glob("frame_*.png"):p.unlink()
    build(); blend=OUT/"scene.blend"; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    wp=OUT/"wrapper"/"eyes.py"; wp.write_text(WRAPPER,encoding="utf-8")
    sp=importlib.util.spec_from_file_location("eye_wrapper",str(wp)); mod=importlib.util.module_from_spec(sp); sp.loader.exec_module(mod)
    eyes=mod.EyesController(str(OUT),MAX_H,MAX_V); base=eyes.pupil_pixels(); checks=[]; passed=True
    for name,h,v,axis,sign in [("Left",-1,0,0,-1),("Right",1,0,0,1),("Up",0,1,1,-1),("Down",0,-1,1,1)]:
        eyes.move(h,v); now=eyes.pupil_pixels(); detail={}
        for s in ("L","R"):
            delta=now[s][axis]-base[s][axis]; ok=delta*sign>2
            detail[s]={"delta_px":round(delta,3),"pass":bool(ok)}; passed &= ok
        checks.append({"direction":name,"eyes":detail,"pass":all(v["pass"] for v in detail.values())})
    eyes.move(1,0); eyes.reset(); rp=eyes.pupil_pixels()
    err=max(abs(rp[s][i]-base[s][i]) for s in ("L","R") for i in (0,1)); resetok=err<.5; passed &= resetok
    checks.append({"direction":"Reset","pass":bool(resetok),"max_pixel_error":round(err,4)})
    (OUT/"validation.json").write_text(json.dumps({"overall_pass":bool(passed),"tests":checks},indent=2),encoding="utf-8")
    records=[]
    for k in range(10):
        t=2*math.pi*k/10; h=math.sin(t); v=math.cos(t); eyes.move(h,v); records.append(eyes.render(k,t,h,v))
        print("Rendered",k)
    (OUT/"metadata.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    eyes.reset(); bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    cards="".join(f'<div><img src="../renders/frame_{k:02d}.png"><b>Frame {k:02d}</b></div>' for k in range(10))
    html='<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:Arial;background:#101b3b;color:white;padding:20px}.g{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}img{width:100%;border-radius:8px}</style></head><body><h1>10 clockwise gaze frames</h1><div class="g">'+cards+'</div></body></html>'
    (OUT/"demo"/"contact_sheet.html").write_text(html,encoding="utf-8")
    (OUT/"README.md").write_text(
        "# Synthetic Eye Movement\\n\\n- scene.blend: editable scene\\n- wrapper/eyes.py: eyes.move(h,v), eyes.reset(), eyes.render(...)\\n- renders/: ten 1024x1024 PNGs\\n- metadata.json: per-frame ground truth and camera matrices\\n- validation.json: five-direction tests\\n- demo/contact_sheet.html: contact sheet\\n\\nRun from Blender > Scripting > Open build_scene.py > Run Script.\\n\\nCamera: 0.40m from eye-pivot midpoint. Fixation target: 0.35m forward. Positive h=right, positive v=up. Procedural demonstration face; not a full MakeHuman/GNM/FLAME asset. Inspect validation.json and renders before submission.\\n",encoding="utf-8")
    # Save a copy of this generator into the submission bundle.
    for txt in bpy.data.texts:
        try:
            if txt.name.lower().endswith("build_scene.py") or (txt.filepath and Path(txt.filepath).name.lower()=="build_scene.py"):
                (OUT/"build_scene.py").write_text(txt.as_string(), encoding="utf-8")
                break
        except: pass
    zpath=OUT.parent/(TEAM+".zip")
    if zpath.exists():zpath.unlink()
    with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob("*"):
            if p.is_file():z.write(p,Path(TEAM)/p.relative_to(OUT))
    print("COMPLETE:",OUT,"ZIP:",zpath,"Direction tests pass:",passed)

if __name__=="__main__":main()
