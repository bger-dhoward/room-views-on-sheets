__title__ = "Create Room\nSheets"
__doc__ = "Create enlarged plans, RCPs, elevations, and axonometric views for all selected rooms and place on sheets"
__author__ = "D. Howard, Ballinger"

import sys
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('Ironpython.wpf')

from Autodesk.Revit.DB import *
from Autodesk.Revit.Creation import *
from Autodesk.Revit.UI.Selection import *
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

import wpf
from System import Windows
from System.Collections.Generic import IList, List

from xyz_utilities import XYZ_element_multiply, translate_X, translate_Y
from viewport_utilities import ViewportHelper

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

active_view = uidoc.ActiveGraphicalView

directions = ["Looking West", "Looking North", "Looking East", "Looking South"]

view_family_types = list(FilteredElementCollector(doc).OfClass(ViewFamilyType))
view_types_map = {}
titleblock_types = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType())
default_titleblock = [t for t in titleblock_types if "B - TB" in t.FamilyName and "30x42" in t.FamilyName][0] # add selector later for titleblock family

for vft in view_family_types:
    name = Element.Name.__get__(vft)
    view_types_map[name] = vft

if "IE - Interior Elevation" in view_types_map:
    elev_view_type = view_types_map["IE - Interior Elevation"]
else:
    elev_view_type = [vft for vft in view_family_types if "Elevation" in vft.FamilyName][0]

plan_view_type = view_types_map["Floor Plan"]
rcp_view_type = view_types_map["Ceiling Plan"]
threeD_view_type = view_types_map["3D View"]

scale = 48
sheet_spacing = 2 / 12 # 2 inches??

forms.alert("Select the rooms to elevate",
    title="Select Rooms",
    ok=True,
    cancel=True,
    exitscript=True,
    )

picked_refs = uidoc.Selection.PickObjects(ObjectType.Element)
picked_rooms = [doc.GetElement(ref) for ref in picked_refs if doc.GetElement(ref).Category.Name == "Rooms"]

# xamlfile = script.get_bundle_file('elevsbyroom_ui.xaml')

# class ToolWindow(Windows.Window):
    # def __init__(self):
        # wpf.LoadComponent(self, xamlfile)

#rooms = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms))
#views = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Views))
#plans = [v for v in views if v.ViewType == ViewType.FloorPlan]

#plan_dict = {plan.Name: plan for plan in plans}
#room_dict = {}
#for room in rooms:
#    key = '{num} - {name}'.format(num = room.Number, name = room.GetParamters('Name')[0].AsValueString())
#    room_dict[key] = {"room_element": room, "level_name": room.Level.Name}

t = Transaction(doc, "Create Elevations from Picked Rooms")
t.Start()

sebo = SpatialElementBoundaryOptions()
elevations = []

views_by_room = {}

#view orientation vectors
forward = XYZ(-1,-1,-1)
upward = XYZ(-0.5, -0.5, 1)
eye_relative = XYZ(50,50,50)

sheet_initial = 610
sheet_number = sheet_initial

anno_crop_offset = 0.0025 #confirm this - there is weird behavior with this variable - seems to jump between decimal feet and decimal inches.

#sheet margin and offset vectors
horizontal_offset = XYZ(-0.25, 0, 0) #offsets to left from sheet origin / previous view
vertical_offset = XYZ(0, 0.25, 0) #offsets upward

#sheet coordinates
sheet_origin = XYZ(0,0,0)
titleblock_origin = XYZ(3.27, 0.06, 0)
default_view_origin = sheet_origin.Add(titleblock_origin).Add(horizontal_offset).Add(vertical_offset)


for room in picked_rooms:
    name = room.GetParameters("Name")[0].AsValueString()
    number = room.Number
    room_key = "{name} - {number}".format(name=name, number=number)
    pt = room.Location.Point

    room_boundary_segments = room.GetBoundarySegments(sebo)[0] #Get first boundary curveloop - may need to be modified 
    boundary_curves = [seg.GetCurve() for seg in room_boundary_segments]
    curve_loop = CurveLoop.Create(List[Curve](boundary_curves))
    plane = curve_loop.GetPlane()
    normal = plane.Normal
    
    expanded_plan_boundary = CurveLoop.CreateViaOffset(curve_loop, -3.5, normal)
    
    #bound_box = room.BoundingBox(uidoc.ActiveGraphicalView)
    level = room.Level
    
    plan = ViewPlan.Create(doc, plan_view_type.Id, level.Id)
    rcp = ViewPlan.Create(doc, rcp_view_type.Id, level.Id)
    plan.Name = "A-EP-48 - " + room_key
    rcp.Name = "A-RCP-48 - " + room_key
    
    plan_views = [plan, rcp]
    
    for view in plan_views:
        view.CropBoxActive = True
        crop_man = view.GetCropRegionShapeManager()
        crop_man.SetCropShape(expanded_plan_boundary)
        anno_crop_param = plan.GetParameters("Annotation Crop")[0]
        anno_crop_param.Set(1) # 1 == True, turn on annotation crop
        crop_man.BottomAnnotationCropOffset = anno_crop_offset
        crop_man.LeftAnnotationCropOffset = anno_crop_offset
        crop_man.TopAnnotationCropOffset = anno_crop_offset
        crop_man.RightAnnotationCropOffset = anno_crop_offset
        view.Scale = scale
        
    
    threeD = View3D.CreateIsometric(doc, threeD_view_type.Id)
    threeD.Name = "A-3D - " +  room_key
    bounding_box = room.BoundingBox[threeD]
    offset_3d = XYZ(1,1,1)
    bounding_box.Max = bounding_box.Max.Add(offset_3d)
    bounding_box.Min = bounding_box.Min.Subtract(offset_3d)
    threeD.SetSectionBox(bounding_box)
    threeD.Scale = scale
    
    eye_pos = pt.Add(eye_relative)
    view_orientation = ViewOrientation3D(eye_pos, upward, forward)
    threeD.SetOrientation(view_orientation)
    threeD.SaveOrientation()
    
    elev_marker = ElevationMarker.CreateElevationMarker(doc, elev_view_type.Id, pt, scale)
    
    sheet = ViewSheet.Create(doc, default_titleblock.Id)
    sheet.Name = "ENLARGED PLANS - {room}".format(room = room_key)
    sheet.SheetNumber = "A{number}".format(number = sheet_number)
    sheet_number += 1
    
    views_by_room[room_key] = { "name": name,
                                "number": number,
                                "room_element": room,
                                "plan": plan,
                                "rcp": rcp,
                                "elevations": [],
                                "sheet": sheet,
                                "3d": threeD,
                                }
    
    
    for i in range(4):
        elev_name = room_key + " " + directions[i]
        elev = elev_marker.CreateElevation(doc, plan.Id, i)
        elev.Name = elev_name
        
        views_by_room[room_key]["elevations"].append(elev)
        
        # elev_cropman = elev.GetCropRegionShapeManager()
        # shape = elev_cropman.GetCropShape()[0]
        # plane = shape.GetPlane()
        # normal = plane.Normal
        # newshape = CurveLoop.CreateViaOffset(shape, 1, normal)
        # elev_cropman.SetCropShape(newshape)

for room_views in views_by_room.values():
    for elev in room_views['elevations']:
        elev_cropman = elev.GetCropRegionShapeManager()
        shape = elev_cropman.GetCropShape()[0]
        plane = shape.GetPlane()
        normal = plane.Normal
        newshape = CurveLoop.CreateViaOffset(shape, 1, normal)
        elev_cropman.SetCropShape(newshape)
        elev.AreAnnotationCategoriesHidden = True
    
    viewtypes = ['plan', 'rcp', '3d', 'elevations']
    
    for viewtype in viewtypes:
        if viewtype != 'elevations':
            room_views[viewtype].AreAnnotationCategoriesHidden = True
        else:
            for view in room_views[viewtype]:
                view.AreAnnotationCategoriesHidden = True
    
    plan_helper = ViewportHelper(room_views['plan'], scale)
    rcp_helper = ViewportHelper(room_views['rcp'], scale)
    
    
    # plan_viewport_diagonal = room_views['plan'].CropBox.Max.Subtract(room_views['plan'].CropBox.Min).Divide(scale)
    # plan_viewport_half_diagonal = plan_viewport_diagonal.Divide(2)
    # plan_viewport_placement = XYZ_element_multiply(plan_viewport_half_diagonal, XYZ(-1,1,0))
    
    # plan_diagonal = room_views['plan'].CropBox.Max.Subtract(room_views['plan'].CropBox.Min)
    # plan_half_diagonal = plan_diagonal.Divide(2)
    # plan_half_diagonal_scaled = plan_half_diagonal.Divide(scale)
    # plan_placement = XYZ_element_multiply(plan_half_diagonal_scaled, XYZ(-1,1,0))
    
    # plan_viewport_origin = default_view_origin.Add(plan_viewport_placement)
    # plan_viewport = Viewport.Create(doc, room_views['sheet'].Id, room_views['plan'].Id, plan_viewport_origin)
    
    plan_viewport = plan_helper.place_at(room_views['sheet'], default_view_origin)
    rcp_viewport = rcp_helper.place_relative_to(room_views['sheet'], default_view_origin, [plan_helper.height_vector, vertical_offset])
    
    # rcp_viewport_origin = translate_Y(default_view_origin, plan_viewport_diagonal.Y).Add(vertical_offset).Add(plan_viewport_placement)
    # rcp_viewport = Viewport.Create(doc, room_views['sheet'].Id, room_views['rcp'].Id, rcp_viewport_origin)
    
    # east_elev_viewport_diagonal = room
    
    # elev_east_viewport_origin = translate_X(default_view_origin, - plan_viewport_diagon.X).Add(horizontal_offset).Add(east_elev_placement)
    
    # line0 = Line.CreateBound(sheet_origin, titleblock_origin)
    # line1 = Line.CreateBound(titleblock_origin, default_view_origin)
    # line2 = Line.CreateBound(default_view_origin, plan_origin)
    
    # doc.Create.NewDetailCurve(room_views['sheet'], line0)
    # doc.Create.NewDetailCurve(room_views['sheet'], line1)
    # doc.Create.NewDetailCurve(room_views['sheet'], line2)
    

t.Commit()



