from Autodesk.Revit.DB import *

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

