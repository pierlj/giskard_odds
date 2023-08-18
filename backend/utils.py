import os
import shutil
import json
import logging
import sqlite3
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

matplotlib.use('agg')

logger = logging.Logger(name="R2D2", level=logging.INFO)

EMPIRE_SCHEMA = {"countdown": int, "bounty_hunters": [{"planet": str, "day": int}]}

FALCON_SCHEMA = {"autonomy": int, "departure": str, "arrival": str, "routes_db": str}

ALLOWED_EXTENSIONS = ["json"]
GRAPH_SAVE_PATH = "frontend/static/ressources/routes_graph.png"


def build_unvierse_graph(db_path: str, millenium_dict: dict) -> nx.Graph:
    """
    Loads the routes file and construct the routes graph of the universe

    Parameters:
        - db_path (str): the path to the .db file.
        - millenium_dict (dict): the Millennium Falcon config dict.

    Returns:
        - G (nx.Graph | None): the NetworkX graph containing all routes information,
                            None if an issue is encountered during the handling of the .db file.
    """
    if os.path.isfile(GRAPH_SAVE_PATH):
        os.remove(GRAPH_SAVE_PATH)
    autonomy = millenium_dict["autonomy"]

    # safely open the DB file.
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()

        # no need to consider routes that cannot be taken by the falcon,
        # i.e. with cost larger than its autonomy
        # (could be done from the query as well)
        db_answer = [row for row in cur.execute("SELECT * FROM ROUTES")]
        assert all(
            [
                edge[0] is not None
                and edge[1] is not None
                and edge[0] != ""
                and edge[1] != ""
                and edge[2] > 0
                for edge in db_answer
            ]
        )
        edge_list = [
            "{} {} {{'weight':{}}}".format(edge[0], edge[1], int(edge[2]))
            for edge in db_answer
            if int(edge[2]) <= autonomy
        ]

        con.close()

    except:
        logger.warn(
            "An issue occurred during the opening of the DB file, route graph was not created."
        )
        return None

    G = nx.parse_edgelist(edge_list, data=True)
    # if the routes graph is small enough create a visualization of the graph to
    # add it on the webapp page.
    if G.number_of_nodes() < 20:  # with more than 20 nodes it might become messy
        try:
            graph_layout = nx.drawing.spring_layout(G)
            color_map = []
            for node in G:
                if node == millenium_dict["departure"]:
                    color_map.append("green")
                elif node == millenium_dict["arrival"]:
                    color_map.append("red")
                else:
                    color_map.append("orange")
            nx.draw_networkx(G, pos=graph_layout, node_color=color_map)
            nx.draw_networkx_edge_labels(
                G,
                graph_layout,
                edge_labels={(u, v): a["weight"] for u, v, a in G.edges(data=True)},
            )
            plt.axis("off")
            legend_handles = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    label="Circle",
                    markerfacecolor="g",
                    markersize=10,
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    label="Circle",
                    markerfacecolor="r",
                    markersize=10,
                ),
            ]
            legend_labels = ["Departure Planet", "Arrival Planet"]
            plt.legend(legend_handles, legend_labels)
            plt.savefig(GRAPH_SAVE_PATH, bbox_inches="tight")
            plt.clf()
        except:
            logger.info('Error during graph visualization creation.')
            if os.path.isfile(GRAPH_SAVE_PATH):
                os.remove(GRAPH_SAVE_PATH)
    return G


def safe_load_json(path: str, schema: dict) -> dict:
    """
    Safely load a .json file and checks if it matches the schema

    Parameters:
        - path (str): the path to the .json file.
        - schema (dict): the schema to compare with

    Returns:
        - loaded_dict (dict | None): the content of the file or None if it does not
                                     match the schema or if the file is incorrect.
    """
    loaded_dict = None
    try:
        with open(path, "r") as f:
            loaded_dict = json.load(f)
        if not check_json_schema(loaded_dict, schema):
            logger.warning(" JSON file has a wrong format.")
            loaded_dict = None
        else:
            logger.info(" Successfully load {} file.".format(path))
            logger.info(loaded_dict)
    except:
        logger.warning(" Error loading {} file.".format(path))
    logger.info(loaded_dict)
    return loaded_dict


def get_json_contents(millenium_path: str, empire_path: str) -> (dict, dict):
    """
    Safely loads the content of the Millennium and Empire .json files.
    """
    millenium_dict = safe_load_json(millenium_path, FALCON_SCHEMA)
    empire_dict = safe_load_json(empire_path, EMPIRE_SCHEMA)

    return millenium_dict, empire_dict


def check_json_schema(dict_check: dict, schema: dict) -> bool:
    """
    Checks wether a dictionnary fits with a type schema.

    Parameters:
        - dict_check (dict): the dictionnary to check.
        - schema (dict): the dictionnary containning the type schema, it contains the keys and type desired,
                         see the example below with the FALCON_SCHEMA:

                         FALCON_SCHEMA = {"autonomy": int, "departure": str, "arrival": str, "routes_db": str}

        Returns:
            - (bool): wether if dict_check matches the schema.
    """
    for key in schema:
        if key not in dict_check:
            logger.info("Missing key: {}, invalid json schema.".format(key))
            return False
        if type(schema[key]) == type:
            if type(dict_check[key]) != schema[key]:
                logger.info(
                    "Wrong type for property {}, invalid json schema.".format(key)
                )
                return False
        elif type(schema[key]) == list:
            if not all(
                [type(schema[key][0]) == type(elem) for elem in dict_check[key]]
            ):
                logger.info(
                    "Wrong type for element in list of property {}, invalid json schema.".format(
                        key
                    )
                )
                return False
            if type(schema[key][0]) == dict and not all(
                [check_json_schema(elem, schema[key][0]) for elem in dict_check[key]]
            ):
                return False

        elif type(schema[key]) == dict:
            return check_json_schema(dict_check[key], schema[key])
    return True


def load_empire_dict(empire_path: str) -> dict:
    """
    Safely loads the content of an empire .json file.
    """
    empire_dict = safe_load_json(empire_path, EMPIRE_SCHEMA)
    return empire_dict


def setup_upload_folder(folder: str):
    """
    Prepare a local folder for the uploading of a .json file inside the webapp.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    else:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.warning("Failed to delete %s. Reason: %s" % (file_path, e))


def allowed_file(filename: str) -> bool:
    """
    Checks if filename has the right extension (i.e. .json here)
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def prettify_path(path: list, itinerary: list[tuple]) -> list:
    """
    Generate a list of steps to make the path and itinerary human-readable.

    Parameters:
        - path (list): a list of the names of the nodes constituting the path from departure to arrival.
        - itinerary (list[tuple]): the associated strategy to achieve the odds contains the arrival
                                   and departure days for each planet in the path.

    Returns:
        - path_str (list[str]): The prettified strings for each step in the itinerary,
                                      if an itinerary is possible.
    """
    path_str = []
    for idx_planet, (planet, (arrival_day, departure_day)) in enumerate(
        zip(path, itinerary)
    ):
        if idx_planet == 0:
            if departure_day - arrival_day == 0:
                path_str.append(
                    "Departure from {} on day {}.".format(planet, arrival_day)
                )
            elif departure_day - arrival_day == 1:
                path_str.append("First stay on {} for 1 day.".format(planet))
            else:
                path_str.append(
                    "First stay on {} for {} days.".format(
                        planet, departure_day - arrival_day
                    )
                )
        elif idx_planet == len(path) - 1:
            path_str.append(
                "Travel from {} to {}, arrival on day {}.".format(
                    previous_planet, planet, arrival_day
                )
            )
            path_str.append("Arrival on {} on day {}.".format(planet, arrival_day))
        else:
            path_str.append(
                "Travel from {} to {}, arrival on day {}.".format(
                    previous_planet, planet, arrival_day
                )
            )
            if departure_day - arrival_day == 1:
                path_str.append("Refuel on {}.".format(planet))
            elif departure_day - arrival_day > 1:
                path_str.append(
                    "Refuel on {} and wait {} days (including refueling day).".format(
                        planet, departure_day - arrival_day
                    )
                )
        previous_planet = planet
        previous_departure = departure_day

    path_str.append("")
    path_str.append("May the force be with you ! ")
    return path_str
