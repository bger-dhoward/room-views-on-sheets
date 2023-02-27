from Autodesk.Revit.DB import *
from System.Collections.Generic import IList, List, IDictionary, Dictionary

def XYZ_element_multiply(basis_XYZ, multiplier_XYZ):
    return XYZ(basis_XYZ.X * multiplier_XYZ.X,
                basis_XYZ.Y * multiplier_XYZ.Y,
                basis_XYZ.Z * multiplier_XYZ.Z)

def translate_X(basis_XYZ, amount):
    """
    Returns new vector of basis vector translated in horizontal (X) by specified amount
    """
    return basis_XYZ.Add(XYZ(amount, 0,0))

def translate_Y(basis_XYZ, amount):
    """
    Returns new vector of basis vector translated in vertical (Y) by specified amount
    """
    return basis_XYZ.Add(XYZ(0, amount, 0))


def get_boundingbox_corner_pts(boundingbox):
    bb_max = boundingbox.Max
    bb_min = boundingbox.Min
    
    # print("bb_max: ", bb_max, "bb_min: ", bb_min)
    
    p0 = XYZ(bb_min.X, bb_min.Y, bb_max.Z)
    p1 = XYZ(bb_max.X, bb_max.Y, bb_max.Z)
    p2 = XYZ(bb_max.X, bb_max.Y, bb_min.Z)
    p3 = XYZ(bb_min.X, bb_min.Y, bb_min.Z)
    
    # print("points: ", p0, p1, p2, p3)
    
    return [p0, p1, p2, p3]

def curveloop_from_points(pointlist):
    line0 = Line.CreateBound(pointlist[0], pointlist[1])
    line1 = Line.CreateBound(pointlist[1], pointlist[2])
    line2 = Line.CreateBound(pointlist[2], pointlist[3])
    line3 = Line.CreateBound(pointlist[3], pointlist[0])
    
    # print("lines: ", line0, line1, line2, line3)
    
    curveloop = CurveLoop.Create(List[Curve]([line0, line1, line2, line3]))
    
    return curveloop

def get_shape_from_boundingbox(boundingbox):
    points = get_boundingbox_corner_pts(boundingbox)
    shape = curveloop_from_points(points)
    
    return shape


def threeD_cropbox_from_room(view, room):
    """
    Adapted from https://thebuildingcoder.typepad.com/blog/2009/12/crop-3d-view-to-room.html
    """
    
    view.CropBoxActive = True
    view.CropBoxVisible = True
    bb = view.CropBox
    transform = bb.Transform
    transformInverse = transform.Inverse
    
    all_pts = []
    
    e = room.ClosedShell
    for ob in e.GetEnumerator():
        edges = ob.Edges
        for edge in edges:
            pts = edge.Tessellate()
            for pt in pts:
                all_pts.append(pt)
    
    vertices_in_3d_view = []
    
    for pt in all_pts:
        vertices_in_3d_view.append(transformInverse.OfPoint(pt))
    
    xMin = 0
    xMax = 0
    yMin = 0
    yMax = 0
    
    first = True
    
    for pt in vertices_in_3d_view:
        if first:
            xMin = pt.X 
            xMax = pt.X
            yMin = pt.Y
            yMax = pt.Y
            first = False
        else:
            if xMin > pt.X:
                xMin = pt.X
            if xMax < pt.X:
                xMax = pt.X
            if yMin > pt.Y:
                yMin = pt.Y
            if yMax < pt.Y:
                yMax = pt.Y
    
    dx = 0.05 * (xMax - xMin)
    dy = 0.05 * (yMax - yMin)
    
    xMin -= dx
    xMax += dx
    
    yMin -= dy
    yMax += dy
    
    bb.Max = XYZ(xMax, yMax, bb.Max.Z)
    bb.Min = XYZ(xMin, yMin, bb.Min.Z)
    
    view.CropBox = bb
    