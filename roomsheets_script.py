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

from xyz_utilities import XYZ_element_multiply, translate_X, translate_Y, get_shape_from_boundingbox, threeD_cropbox_from_room
from viewport_utilities import ViewportHelper

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

active_view = uidoc.ActiveGraphicalView

directions = ["Looking West", "Looking North", "Looking East", "Looking South"]

# tb_name_pt1 = "B - TB"
# tb_name_pt2 = "30x42"

tb_name_pt1 = "SG_TB_CD_NYPCC"
tb_name_pt2 = "36X48"

scale = 32
sheet_spacing = 2 / 12 # 2 inches??

view_family_types = list(FilteredElementCollector(doc).OfClass(ViewFamilyType))
view_types_map = {}
titleblock_types = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType())
default_titleblock = [t for t in titleblock_types if tb_name_pt1 in t.FamilyName and tb_name_pt2 in t.GetParameters("Type Name")[0].AsValueString()][0] # add selector later for titleblock family

rooms_category = Category.GetCategory(doc, BuiltInCategory.OST_Rooms)

for vft in view_family_types:
    name = Element.Name.__get__(vft)
    view_types_map[name] = vft

if "SG_interior Elevation" in view_types_map:
    elev_view_type = view_types_map["SG_interior Elevation"]
else:
    elev_view_type = [vft for vft in view_family_types if "Elevation" in vft.FamilyName][0]

plan_view_type = view_types_map["SG_Floor Plan"]
rcp_view_type = view_types_map["SG_Ceiling Plan"]
# plan_view_type = view_types_map["Floor Plan"]
# rcp_view_type = view_types_map["Ceiling Plan"]
threeD_view_type = view_types_map["3D View"]



forms.alert("Select the rooms to elevate",
    title="Select Rooms",
    ok=True,
    cancel=True,
    exitscript=True,
    )

picked_refs = uidoc.Selection.PickObjects(ObjectType.Element)
picked_rooms = [doc.GetElement(ref) for ref in picked_refs if doc.GetElement(ref).Category.Name == "Rooms"]


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
titleblock_origin = XYZ(2.66135, 0.23664, 0)
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
        view.ViewTemplateId = ElementId(-1)
        view.AreAnnotationCategoriesHidden = True
        view.CropBoxActive = True
        crop_man = view.GetCropRegionShapeManager()
        crop_man.SetCropShape(expanded_plan_boundary)
        anno_crop_param = view.GetParameters("Annotation Crop")[0]
        anno_crop_param.Set(1) # 1 == True, turn on annotation crop
        crop_man.BottomAnnotationCropOffset = anno_crop_offset
        crop_man.LeftAnnotationCropOffset = anno_crop_offset
        crop_man.TopAnnotationCropOffset = anno_crop_offset
        crop_man.RightAnnotationCropOffset = anno_crop_offset
        view.Scale = scale

        
    

    
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
                                "elevations": list(),
                                "sheet": sheet,
                                "3d": None,
                                }
    
    
    for i in range(len(directions)):
        elev_name = room_key + " " + directions[i]
        elev = elev_marker.CreateElevation(doc, plan.Id, i)
        elev.ViewTemplateId = ElementId(-1)
        elev.Name = elev_name
        elev.AreAnnotationCategoriesHidden = True
        elev.AreImportCategoriesHidden = True
        # elev.IsolateCategoryTemporary(rooms_category.Id)
        elev.Scale = scale
        
        elev.SetCategoryHidden(rooms_category.Id, False) 
        bb = room.BoundingBox[elev]
        room_shape = get_shape_from_boundingbox(bb)
        plane = room_shape.GetPlane()
        normal = plane.Normal
        # print("room shape len:", room_shape.GetExactLength())
        # print("roomshape w,h", room_shape.GetRectangularWidth(plane), room_shape.GetRectangularHeight(plane))
        # print("roomshape ccw?", room_shape.IsCounterclockwise(normal))
        elev_cropman = elev.GetCropRegionShapeManager()
        
        newshape = CurveLoop.CreateViaOffset(room_shape, 1, normal)
        # print("new shape len:", newshape.GetExactLength())
        # print("new w,h", newshape.GetRectangularWidth(plane), newshape.GetRectangularHeight(plane))
        # print("new shape ccw?", newshape.IsCounterclockwise(normal))
        elev_cropman.SetCropShape(newshape)
        print("crop valid?", elev_cropman.IsCropRegionShapeValid(newshape))
        
        views_by_room[room_key]["elevations"].append(elev)
        
        elev_cropman.Dispose()
        newshape.Dispose()
        bb.Dispose()
        room_shape.Dispose()
    
    elev_marker.Dispose()
        
    threeD = View3D.CreateIsometric(doc, threeD_view_type.Id)
    threeD.Name = "A-3D - " +  room_key
    bounding_box = room.BoundingBox[threeD]
    offset_3d = XYZ(1,1,1)
    bounding_box.Max = bounding_box.Max.Add(offset_3d)
    bounding_box.Min = bounding_box.Min.Subtract(offset_3d)
    threeD.SetSectionBox(bounding_box)
    threeD.Scale = scale
    threeD.AreAnnotationCategoriesHidden = True
    threeD.CropBoxActive = True
    #threeD.SetCategoryHidden(scope_box.Id, True) #scope boxed not defined in api?
    
    eye_pos = pt.Add(eye_relative)
    view_orientation = ViewOrientation3D(eye_pos, upward, forward)
    threeD.SetOrientation(view_orientation)
    threeD.SaveOrientation()
    
    threeD_cropbox_from_room(threeD, room)
    
    views_by_room[room_key]['3d'] = threeD

for room_views in views_by_room.values():
    room = room_views['room_element']
    print(room_views['name'])
    
    sheet = room_views['sheet']
    
    plan_helper = ViewportHelper(room_views['plan'], scale)
    rcp_helper = ViewportHelper(room_views['rcp'], scale)
    
    plan_viewport = plan_helper.place_at(sheet, default_view_origin)
    rcp_viewport = rcp_helper.place_relative_to(sheet, default_view_origin, [plan_helper.height_vector, vertical_offset])
    
    elev_west_helper =  ViewportHelper(room_views['elevations'][0], scale)
    # print("west:  ", elev_west_helper.viewport_placement.ToString())
    elev_north_helper = ViewportHelper(room_views['elevations'][1], scale)
    # print("north: ", elev_north_helper.viewport_placement.ToString())
    elev_east_helper =  ViewportHelper(room_views['elevations'][2], scale)
    # print("east:  ", elev_east_helper.viewport_placement.ToString())
    elev_south_helper = ViewportHelper(room_views['elevations'][3], scale)
    # print("south: ", elev_south_helper.viewport_placement.ToString())
    
    # elev_south_viewport = elev_south_helper.place_relative_to(sheet, default_view_origin, [- plan_helper.width_vector, horizontal_offset])
    # elev_east_viewport = elev_east_helper.place_relative_to(sheet, elev_south_helper.viewport_ref, [- elev_south_helper.width_vector, horizontal_offset])
    # elev_north_viewport = elev_north_helper.place_relative_to(sheet, elev_south_helper.viewport_ref, [elev_south_helper.height_vector, vertical_offset])
    # elev_west_viewport = elev_west_helper.place_relative_to(sheet, elev_north_helper.viewport_ref, [- elev_north_helper.width_vector, horizontal_offset])
    elev_east_viewport = elev_east_helper.place_relative_to(sheet, 
                                                            default_view_origin, 
                                                            [-plan_helper.width_vector, horizontal_offset])
    elev_north_viewport = elev_north_helper.place_relative_to(sheet, 
                                                            elev_east_helper.viewport_ref, 
                                                            [- elev_east_helper.width_vector, horizontal_offset])
    elev_west_viewport = elev_west_helper.place_relative_to(sheet, 
                                                            elev_east_helper.viewport_ref, 
                                                            [elev_east_helper.height_vector, vertical_offset])
    elev_south_viewport = elev_south_helper.place_relative_to(sheet, 
                                                            elev_west_helper.viewport_ref, 
                                                            [- elev_west_helper.width_vector, horizontal_offset])
    
    threeD_helper = ViewportHelper(room_views['3d'], scale)
    threeD_viewport = threeD_helper.place_relative_to(sheet,
                                                        elev_north_helper.viewport_ref,
                                                        [- elev_north_helper.width_vector, horizontal_offset])
    
    
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



