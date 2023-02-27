from Autodesk.Revit.DB import *
from Autodesk.Revit.Creation import *
from pyrevit import revit, DB

from xyz_utilities import XYZ_element_multiply, translate_X, translate_Y

doc = __revit__.ActiveUIDocument.Document

class ViewportHelper:
    global doc
    
    def __init__(self, view, scale):
        self.view = view
        self.scale = scale
    
        self.viewport_diagonal = self.view.CropBox.Max.Subtract(self.view.CropBox.Min).Divide(self.scale)
        print("cb max:", self.view.CropBox.Max.ToString(), "cb min:", self.view.CropBox.Min.ToString())
        print(self.view.Name, "diagonal: ", self.viewport_diagonal.ToString())
        self.viewport_half_diagonal = self.viewport_diagonal.Divide(2)
        self.viewport_placement = XYZ_element_multiply(self.viewport_half_diagonal, XYZ(-1,1,0))
        
        self.width_vector = XYZ(self.viewport_diagonal.X, 0, 0)
        self.height_vector = XYZ(0, self.viewport_diagonal.Y, 0)
    
    def place_at(self, sheet, origin):
        self.viewport_ref  = origin
        self.viewport_origin = self.viewport_ref.Add(self.viewport_placement)
        return Viewport.Create(doc, sheet.Id, self.view.Id, self.viewport_origin)
        
    def place_relative_to(self, sheet, origin, relations):
        self.viewport_ref = origin
        for relation in relations:
            # print("relation: ", relation.ToString())
            self.viewport_ref = self.viewport_ref.Add(relation)
        self.viewport_origin = self.viewport_ref.Add(self.viewport_placement)
        # print(self.view.Name, "vp_orig: ", self.viewport_origin.ToString())
        # print("vp_ref: ", self.viewport_ref.ToString())
        # print("vp_placement: ", self.viewport_placement.ToString())
        return Viewport.Create(doc, sheet.Id, self.view.Id, self.viewport_origin)