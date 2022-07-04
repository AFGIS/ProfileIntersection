import arcpy
import os

intersectionLayer = arcpy.GetParameterAsText(0)
inputProfileRoute = arcpy.GetParameterAsText(1)
inputFeatures = [str(intersectionLayer), str(inputProfileRoute)]
inputDepthRaster = arcpy.GetParameterAsText(2)
arcpy.env.workspace = arcpy.GetParameterAsText(3)
outputFileName = arcpy.GetParameterAsText(4)
exaggeration = float(arcpy.GetParameterAsText(5))/float(arcpy.GetParameterAsText(6))
spatial_ref = arcpy.Describe(intersectionLayer).spatialReference
exaggerationDepthFieldName = "Depth_m_Ex" + str(int(exaggeration))


def findDepth(points, route, depthRaster):
    arcpy.management.AddField(points, "Depth_m", "DOUBLE")
    arcpy.management.AddField(points, exaggerationDepthFieldName, "DOUBLE")
    arcpy.management.AddField(points, "Easting", "DOUBLE")
    arcpy.management.AddField(points, "Northing", "DOUBLE")

    arcpy.management.CalculateField(points, "Easting", "!SHAPE.CENTROID.X!", "PYTHON_9.3")
    arcpy.management.CalculateField(points, "Northing", "!SHAPE.CENTROID.Y!", "PYTHON_9.3")

    with arcpy.da.UpdateCursor(points, ("Easting", "Northing", "Depth_m", exaggerationDepthFieldName)) as cursor:
        for row in cursor:
            result = arcpy.GetCellValue_management(depthRaster, str(row[0]) + " " + str(row[1]))
            CellValue = float(result.getOutput(0).replace(',', '.'))
            row[2] = -abs(CellValue)
            row[3] = -abs(CellValue) * exaggeration
            cursor.updateRow(row)
    return points


def addKP(ddp):
    if arcpy.Exists("DDP_KP"):
        arcpy.Delete_management("DDP_KP")
    KP_Table = arcpy.lr.LocateFeaturesAlongRoutes(ddp, inputProfileRoute,radius_or_tolerance=10,
                                                  route_id_field="LINE_NAME", out_table="DDP_KP",
                                                  out_event_properties="RID POINT KP_M")
    arcpy.management.AddField(KP_Table, "Y", "DOUBLE")
    arcpy.management.CalculateField(KP_Table, "Y", "!" + exaggerationDepthFieldName + "!", "PYTHON_9.3")
    addBarPoints(KP_Table)
    temp_layer1 = "Temp1"
    arcpy.management.MakeXYEventLayer(KP_Table, 'KP_M', "Y", temp_layer1, spatial_ref)
    if arcpy.Exists(outputFileName):
        arcpy.Delete_management(outputFileName)
    outputDataset = arcpy.CopyFeatures_management(temp_layer1, outputFileName)
    arcpy.management.AddField(outputDataset, "RouteFeature", "TEXT")
    arcpy.management.CalculateField(outputDataset, "RouteFeature", "\"" + str(os.path.basename(inputProfileRoute))
                                    + "\"", "PYTHON_9.3")

def addBarPoints(table):
    arcpy.management.AddField(table, "Type", "TEXT")
    with arcpy.da.UpdateCursor(table, "Type") as cursor:
        for row in cursor:
            row[0] = "Profile"
            cursor.updateRow(row)
    barPoints = arcpy.management.Copy(table, "BarPoints")
    with arcpy.da.UpdateCursor(table, "Type") as cursor:
        for row in cursor:
            row[0] = "Bar"
            cursor.updateRow(row)
    arcpy.management.CalculateField(barPoints, "Y", 0, "PYTHON_9.3")
    arcpy.management.Append(barPoints, table)


def cleanUp():
    arcpy.Delete_management("Centroids")
    arcpy.Delete_management("DDP_KP")
    arcpy.Delete_management("BarPoints")

def init():
    intersections = arcpy.analysis.Intersect(inputFeatures, outputFileName, output_type="POINT")
    addKP(findDepth(intersections, inputProfileRoute, inputDepthRaster))
    cleanUp()

init()




