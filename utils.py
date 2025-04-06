import pycristoforo as pyc
import random, re, csv
from shapely.geometry import Point
from pyproj import Geod
from bs4 import BeautifulSoup
from datetime import datetime
from shapely.geometry.polygon import Polygon
import json

geod = Geod(ellps="WGS84")
sqllite_file = r'data/random_latlong.db'
csv_file = r'data/random_latlong.csv'


def get_area(poly):
    """
    Given a polygon return area in m^2
    :param poly:
    :return:
    """
    area = abs(geod.geometry_area_perimeter(poly)[0])
    return area

def get_sample_latlong(country_name='Canada', num_points=100):
    country = pyc.get_shape(country_name)
    points = pyc.geoloc_generation(country, 100, country_name)
    #get list of latlongs
    latlong_list = []
    for i in points:
        # reverse the coordinates - it seems the order is long, lat
        # see https://github.com/AleNegrini/PyCristoforo/issues/34
        latlong = i['geometry']['coordinates'][-1::-1]
        latlong_list.append(latlong)
    return latlong_list


def get_random_point_in_polygon(poly):
    minx, miny, maxx, maxy = poly.bounds
    while True:
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if poly.contains(p):
            return p


def extract_latlong_from_kml(kml_file):
    """
    A simple kml processort that returns a list of latlong tuples.
    :param filepath:
    :return:
    """

    with open(kml_file, 'r') as myfile:
        doc = myfile.read()

    soup = BeautifulSoup(doc, "lxml")
    required0 = soup.find_all("coordinates")
    xy = []
    for i in required0:
        xy.append(i.get_text())
    # assert len(xy) == 1  # not sure how to handle multiple lists
    if len(xy) > 1:
        print("We have multiple polygons.")
    polys = []
    for curr_poly in xy:
        toks = re.split(r'\s+', curr_poly)
        coords = []
        for tok in toks:
            if tok == '':
                continue
            temp = list(reversed(list(map(float, tok.split(",")[:2]))))
            # print(temp)
            coords.append(temp)
        # print(xy)
        polys.append(coords)
    print(f"Found {len(polys)} polygons/disjoint regions.")
    return polys


def parse_kml(kml_file, op_file, debug_file=None):
    """
    Simple converter from kml to json - note might break on complext inputs, use libraries ike ogr2ogr for them
    :param kml_file: the downloaded kml file
    :param op_file: this is a json file thats created after parsing the kml file
    :param debug_file: if specified, coordinates of disjoint regions from the kml files are bundled together and
        written out as csv; this can be uploaded to google my maps to see the markers.
    :return:
    """
    polys = extract_latlong_from_kml(kml_file)
    j = {}
    all_coords = []
    with open(op_file, 'w') as fw:
        for p_idx, coords in enumerate(polys):
            poly_name = f"polygon_{p_idx}"
            j[poly_name] = coords
            all_coords += coords
            # for idx, c in enumerate(coords):
            print(f"For polygon {poly_name}, # coordinates={len(coords)}.")
    print(f"Total coordinates: {len(all_coords)}.")
    with open(op_file, 'w') as fw:
        fw.write(json.dumps(j, indent=4))
    if debug_file:
        with open(debug_file, 'w') as fw_debug:
            fw_debug.write(f"title,latitude,longitude\n")
            for idx, c in enumerate(all_coords):
                fw_debug.write(f"{idx},{c[0]},{c[1]}\n")

    print(f"Written output to {op_file}.")


def generate_random_points_multiregion(parsed_kml_json, num_points, output_csv):
    """
    Samples points from possibly multiple regions as specified in the "parsed_kml_json" file. For each region the num of
    points sampled from it are in proportion to the area of the region.
    :param parsed_kml_json:
    :param num_points:
    :param output_csv: this has an aggregate of all generated coordinates
    :return:
    """
    with open(parsed_kml_json) as f:
        j = json.load(f)
    print(f"{len(j)} polygons found.")
    points_per_poly = {}
    poly_areas = {}
    for polyname, coords in j.items():
        # pyrpoj expects lon-lat
        p = Polygon([list(reversed(c)) for c in coords])
        area = get_area(p)
        poly_areas[polyname] = area
        print(f"Polyon {polyname}, with {len(coords)} coordinates, has area {area*1e-6: .2f} km^2.")
    total_area = sum(poly_areas.values())
    for p, a in poly_areas.items():
        points_per_poly[p] = int(num_points * (1.0 * a / total_area))
    total_points = sum(points_per_poly.values())
    # we might have some points leftover due to rounding
    # assign to a randomly picked polygon
    residual = num_points - total_points
    temp = list(points_per_poly.keys())
    random_key = temp[random.randint(0, len(points_per_poly)-1)]
    points_per_poly[random_key] += residual

    random_coords = []
    for polyname, n in points_per_poly.items():
        print(f"for polygon {polyname}, {n} to be generated.")
        poly = Polygon(j[polyname])
        p_random_coords = generate_random_points_in_shape(poly, n, None)
        # cast in case we get numpy array
        random_coords += list(p_random_coords)

    with open(output_csv, 'w') as fw:
        fw.write(f"title,latitude,longitude\n")
        for idx, c in enumerate(random_coords):
            fw.write(f"{idx},{c[0]},{c[1]}\n")


def generate_random_points_in_shape(poly, num_points, output_csv=None):
    """
    This function assumes the first col is the marker name, the second col is lat, third col is long.
    For different format modify this function.
    :param poly: a shapely polygon object
    :param num_points number of points to sample
    :param output_csv: if specified output it written to this file
    :return:
    """
    random_coords = []
    for i in range(num_points):
        point_in_poly = get_random_point_in_polygon(poly)
        random_coords.append((point_in_poly.x, point_in_poly.y))
    if output_csv:
        with open(output_csv,'w') as fw:
            for idx, c in enumerate(random_coords):
                fw.write(f"{idx},{c[0]},{c[1]}\n")
    return random_coords


def demo():

    # kml_file = r'data/contours.kml'  # downloaded from google my maps
    # parsed_kml_file = r'data/parsed_kml.json'  # result of parsing the kml file are written here
    # kml_as_csv_file = r'data/kml_as_csv.csv' # this is a debug file - can be uploaded to check if we got all vertices
    # random_points_op_file = r'data/generated_from_multiregion.csv' # the output we really want

    kml_file = r'D:/project/cac/campaign/2021/boston_pizza/contours.kml'  # downloaded from google my maps
    parsed_kml_file = r'D:/project/cac/campaign/2021/boston_pizza/parsed_kml.json'  # result of parsing the kml file are written here
    kml_as_csv_file = r'D:/project/cac/campaign/2021/boston_pizza/kml_as_csv.csv'  # this is a debug file - can be uploaded to check if we got all vertices
    random_points_op_file = r'D:/project/cac/campaign/2021/boston_pizza/generated_from_multiregion.csv'  # the output we really want
    num_points = 500000 # number of points we want to sample


    # lets measure the time taken to generate
    t1 = datetime.now()

    # parse the kml file, this can have multiple disjoint regions
    parse_kml(kml_file, parsed_kml_file, kml_as_csv_file)

    # generate random points within this region, where the # points in a region is proportional to the area
    generate_random_points_multiregion(parsed_kml_file, num_points, random_points_op_file)
    t2 = datetime.now()
    print(f"Time to generate {num_points} points is {(t2-t1).total_seconds()} sec.")


if __name__ == "__main__":
    demo()
