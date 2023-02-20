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
    
        self.viewport_diagonal = view.CropBox.Max.Subtract(view.CropBox.Min).Divide(scale)
        self.viewport_half_diagonal = self.viewport_diagonal.Divide(2)
        self.viewport_placement = XYZ_element_multiply(self.viewport_half_diagonal, XYZ(-1,1,0))
        
        self.width_vector = XYZ(self.viewport_diagonal.X, 0, 0)
        self.height_vector = XYZ(0, self.viewport_diagonal.Y, 0)
    
    def place_at(self, sheet, origin):
        self.viewport_origin  = origin.Add(self.viewport_placement)
        return Viewport.Create(doc, sheet.Id, self.view.Id, self.viewport_origin)
        
    def place_relative_to(self, sheet, origin, relations):
        self.viewport_origin = origin.Add(self.viewport_placement)
        for relation in relations:
            self.viewport_origin = self.viewport_origin.Add(relation)
        return Viewport.Create(doc, sheet.Id, self.view.Id, self.viewport_origin)