# This program is used in the first step of the Treepedia project to get points along street 
# network to feed into GSV python scripts for metadata generation.
# Copyright(C) Xiiaojiang Li, Marwa Abdulhai, Ian Seiferling Senseable City Lab, MIT 
# First version July 21 2017

# update to the python3, deal with the version issue of pyproj
# second version Dec 5, 2020


# now run the python file: createPoints.py, the input shapefile has to be in projection of WGS84, 4326
def createPoints(inshp, outshp, mini_dist):
    
    '''
    This function will parse throigh the street network of provided city and
    clean all highways and create points every mini_dist meters (or as specified) along
    the linestrings
    Required modules: Fiona and Shapely

    parameters:
        inshp: the input linear shapefile, must be in WGS84 projection, ESPG: 4326
        output: the result point feature class
        mini_dist: the minimum distance between two created point

    modified by May 2ed, 2018, consider the linestring and multi-linear string
    last modified by Xiaojiang Li, MIT Senseable City Lab
    
    '''
    
    import fiona
    import os,os.path
    from shapely.geometry import shape,mapping
    from shapely.ops import transform
    from functools import partial
    import pyproj
    from fiona.crs import from_epsg
    from shapely.geometry import LineString, Point # To create line geometries that can be used in a GeoDataFrame
    import math
    
    count = 0
    # s = {'trunk_link','tertiary','motorway','motorway_link','steps', None, ' ','pedestrian','primary', 'primary_link','footway','tertiary_link', 'trunk','secondary','secondary_link','tertiary_link','bridleway','service'}
    # s = {'trunk_link','tertiary','motorway','motorway_link','steps', ' ','pedestrian','primary', 'primary_link','footway','tertiary_link', 'trunk','secondary','secondary_link','tertiary_link','bridleway','service'}
    s = {}
    
    # the temporaray file of the cleaned data
    root = os.path.dirname(inshp)
    basename = 'clean_' + os.path.basename(inshp)
    temp_cleanedStreetmap = os.path.join(root,basename)
    
    # if the tempfile exist then delete it
    if os.path.exists(temp_cleanedStreetmap):
        fiona.remove(temp_cleanedStreetmap, 'ESRI Shapefile')
        print ('removed the existed tempfile')
        
    # clean the original street maps by removing highways, if it the street map not from Open street data, users'd better to clean the data themselve
    with fiona.open(inshp) as source, fiona.open(temp_cleanedStreetmap, 'w', driver=source.driver, crs=source.crs,schema=source.schema) as dest:
        for feat in source:
            try:
                i = feat['properties']['highway'] # for the OSM street data
                # i = feat['properties']['fclass'] # for the OSM tokyo street data
                if i in s:
                    continue
            except:
                # if the street map is not osm, do nothing. You'd better to clean the street map, if you don't want to map the GVI for highways
                key = list(dest.schema['properties'].keys())[0]
                # key = dest.schema['properties'].keys()[0] # get the field of the input shapefile and duplicate the input feature
                i = feat['properties'][key]
                if i in s:
                    continue

            # print feat
            dest.write(feat)
            
    schema = {
        'geometry': 'Point',
        'properties': {'id': 'int'},
    }
    
    
    # Create point along the streets
    # with fiona.drivers():
    with fiona.Env():
        #with fiona.open(outshp, 'w', 'ESRI Shapefile', crs=source.crs, schema) as output:
        with fiona.open(outshp, 'w', crs = from_epsg(4326), driver = 'ESRI Shapefile', schema = schema) as output:
            i = 0
            for line in fiona.open(temp_cleanedStreetmap):
                i = i + 1
                if i %100 == 0: print(i)
                # try: 
                # deal with MultiLineString and LineString
                featureType = line['geometry']['type']
                
                # for the LineString
                if featureType == "LineString":
                    first = shape(line['geometry'])
                    length = first.length
                    
                    # deal with different version of pyproj
                    if pyproj.__version__[0]!='2':
                        project = partial(pyproj.transform,pyproj.Proj(init='EPSG:4326'),pyproj.Proj(init='EPSG:3857')) #3857 is psudo WGS84 the unit is meter
                        line2 = transform(project, first)
                    else:
                        project = pyproj.Transformer.from_crs(4326, 3857, always_xy=True)

                        # loop all vertices in the line and then reproj
                        line2_coord = []
                        for (lon, lat) in first.coords:    
                            x, y = project.transform(lon, lat)
                            line2_coord.append((x, y))
                        line2 = LineString(line2_coord)


                    # line2 = transform(project, first)
                    linestr = list(line2.coords)
                    dist = mini_dist 

                    if math.isnan(line2.length): continue

                    for distance in range(0,int(line2.length), dist):
                        point = line2.interpolate(distance)
                        # project2 = partial(pyproj.transform,pyproj.Proj(init='EPSG:3857'),pyproj.Proj(init='EPSG:4326'))

                        if pyproj.__version__[0]!='2':
                            project2 = partial(pyproj.transform,pyproj.Proj(init='EPSG:3857'),pyproj.Proj(init='EPSG:4326')) #3857 is psudo WGS84 the unit is meter
                            point = transform(project2, point)
                        else:
                            project2 = pyproj.Transformer.from_crs(3857, 4326, always_xy=True)
                            point = Point(project2.transform(point.x, point.y))
                            
                        output.write({'geometry':mapping(point),'properties': {'id':1}})
                

                # for the MultiLineString, seperate these lines, then partition those lines
                elif featureType == "MultiLineString":
                    multiline_geom = shape(line['geometry'])
                    print ('This is a multiline')
                    for singleLine in multiline_geom:
                        length = singleLine.length
                        
                        # partion each single line in the multiline
                        # project = partial(pyproj.transform,pyproj.Proj(init='EPSG:4326'),pyproj.Proj(init='EPSG:3857')) #3857 is psudo WGS84 the unit is meter

                        if pyproj.__version__[0]!='2':
                            project = partial(pyproj.transform,pyproj.Proj(init='EPSG:4326'),pyproj.Proj(init='EPSG:3857')) #3857 is psudo WGS84 the unit is meter
                            line2 = transform(project, singleLine)
                        else:
                            project = pyproj.Transformer.from_crs(4326, 3857, always_xy=True)
                              
                            # loop all vertices in the line and then reproj
                            line2_coord = []
                            for (lon, lat) in singleLine.coords:    
                                x, y = project.transform(lon, lat)
                                line2_coord.append((x, y))
                            line2 = LineString(line2_coord)


                        linestr = list(line2.coords)
                        dist = mini_dist #set
                        
                        for distance in range(0,int(line2.length), dist):
                            point = line2.interpolate(distance)
                            # project2 = partial(pyproj.transform,pyproj.Proj(init='EPSG:3857'),pyproj.Proj(init='EPSG:4326'))

                            if pyproj.__version__[0]!='2':
                                project2 = partial(pyproj.transform,pyproj.Proj(init='EPSG:3857'),pyproj.Proj(init='EPSG:4326')) #3857 is psudo WGS84 the unit is meter
                                point = transform(project2, point)
                            else:
                                project2 = pyproj.Transformer.from_crs(3857, 4326, always_xy=True)
                                point = Point(project2.transform(point.x, point.y))
                                
                            output.write({'geometry':mapping(point),'properties': {'id':1}})
                    
                    else:
                        print('Else--------')
                        continue
                        
                # except:
                #     print ("You should make sure the input shapefile is WGS84")
                #     return

    print("Process Complete")
    
    # delete the temprary cleaned shapefile
    fiona.remove(temp_cleanedStreetmap, 'ESRI Shapefile')







# Example to use the code, 
# Note: make sure the input linear featureclass (shapefile) is in WGS 84 or ESPG: 4326
# ------------main ----------
if __name__ == "__main__":
    import os,os.path
    import sys
    
    # set as your own filename
    inshp = '../sample-spatialdata/CambridgeStreet_wgs84.shp'
    outshp = '../sample-spatialdata/Cambridge20m.shp'
    
    mini_dist = 20 #the minimum distance between two generated points in meter
    createPoints(inshp, outshp, mini_dist)
