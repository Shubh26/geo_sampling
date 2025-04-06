
import pycristoforo as pyc
import numpy as np
import random, re, csv
from shapely.geometry import Point, LineString, Polygon
from bs4 import BeautifulSoup
from datetime import datetime
sqllite_file = r'data/random_latlong.db'
csv_file = r'data/random_latlong.csv'

def get_sample_latlong(country_name='Canada', num_points=100):
    country = pyc.get_shape(country_name)
    points = pyc.geoloc_generation(country, 100, country_name)
    # get list of latlongs
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
    assert len(xy) == 1  # not sure how to handle multiple lists
    toks = re.split(r'\s+', xy[0])
    coords = []
    for tok in toks:
        if tok == '':
            continue
        temp = list(reversed(list(map(float, tok.split(",")[:2]))))
        # print(temp)
        coords.append(temp)
    # print(xy)
    return coords

def convert_kml_to_csv(kml_file, op_file):
    """
    Simple converter from kml to csv - note might break on complext inputs, use libraries ike ogr2ogr for them
    :param kml_file:
    :param op_file:
    :return:
    """
    coords = extract_latlong_from_kml(kml_file)
    # print(coords)
    with open(op_file, 'w') as fw:
        for idx, c in enumerate(coords):
            fw.write(f"{idx},{c[0]},{c[1]}\n")
    print(f"Written output to {op_file}.")

def generate_random_points_inn_shape(latlong_csv, num_points, output_csv):
    """
    This function assumes the first col is the marker name, the second col is lat, third col is long.
    For different format modify this function.
    :param latlong_csv:
    :return:
    """
    coords = []
    with open(latlong_csv, 'r') as csvfile:
        temp = csv.reader(csvfile, delimiter=',')
        # temp = np.asarray(temp, dtype='float')
        for row in temp:
            coords.append(row[1:])
    coords = np.asarray(coords, dtype='float')
    # print(coords)
    p = Polygon(coords)
    random_coords = []
    for i in range(num_points):
        point_in_poly = get_random_point_in_polygon(p)
        random_coords.append((point_in_poly.x, point_in_poly.y))
    with open(output_csv ,'w') as fw:
        for idx, c in enumerate(random_coords):
            fw.write(f"{idx},{c[0]},{c[1]}\n")

if __name__ == "__main__":
    # latlong_list = get_sample_latlong(num_points=10)
    # print(f"Created latlong list with {len(latlong_list)}  items.")
    # df = pd.DataFrame(columns=['index', 'latitude', 'longitude'])
    # for idx, (latitude, longitude) in enumerate(latlong_list):
    #     df = df.append({'index': idx, 'latitude': latitude, 'longitude': longitude}, ignore_index=True)
    # conn = sql.connect(sqllite_file)
    # df.to_sql('random_latlong', conn)
    # df[['latitude', 'longitude']].to_csv(path_or_buf=csv_file, header=False, index=False)

    kml_file = r'data/contour.kml'
    kml_as_csv_file = r'data/kml_as_csv.csv'
    random_points_op_file = r'data/generated_from_shape.csv'
    num_points = 10000
    # lets measure the time taken to generate
    t1 = datetime.now()
    convert_kml_to_csv(kml_file, kml_as_csv_file)
    generate_random_points_inn_shape(kml_as_csv_file, 1000, random_points_op_file)
    t2 = datetime.now()
    print(f"Time to generate {num_points} points is {(t 2 -t1).total_seconds()} sec.")