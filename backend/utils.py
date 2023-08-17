import os
import shutil
import json
import logging
import sqlite3
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


logger = logging.getLogger(name="R2D2")

EMPIRE_SCHEMA = {"countdown": int, "bounty_hunters": [{"planet": str, "day": int}]}

FALCON_SCHEMA = {"autonomy": int, "departure": str, "arrival": str, "routes_db": str}

ALLOWED_EXTENSIONS = ["json"]
GRAPH_SAVE_PATH = "frontend/static/ressources/routes_graph.png"


def build_unvierse_graph(db_path, millenium_dict):
    os.remove(GRAPH_SAVE_PATH)
    autonomy = millenium_dict["autonomy"]
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()

        # no need to consider routes that cannot be taken by the falcon (could be done from the query as well)
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
    if G.number_of_nodes() < 50:  # if the routes graph is not too large display it
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
    return G


def safe_load_json(path, schema):
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


def get_json_contents(millenium_path, empire_path):
    millenium_dict = safe_load_json(millenium_path, FALCON_SCHEMA)
    empire_dict = safe_load_json(empire_path, EMPIRE_SCHEMA)

    return millenium_dict, empire_dict


def check_json_schema(dict_check, schema):
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


def load_empire_dict(empire_path):
    empire_dict = safe_load_json(empire_path, EMPIRE_SCHEMA)
    return empire_dict


def setup_upload_folder(folder):
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


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def prettify_path(path, itinerary):
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
                path_str.append("First stay on {} for 1 days.".format(planet))
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
