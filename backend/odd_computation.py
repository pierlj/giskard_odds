import argparse
import os
import networkx as nx
import itertools
from collections import defaultdict
import logging

from utils import *

logging.basicConfig(level=logging.INFO)

def compute_path_length(
    path: list, universe_graph: nx.Graph, autonomy: int
) -> (int, int, int):
    """
    Compute the length of a path given the route graph and autonomy of the Falcon

    Parameters:
        - path (list): a list of the names of the nodes constituting the path from departure to arrival.
        - universe_graph (nx.Graph): NetworkX graph representing the possible routes in the universe.
        - autonomy (int): the autonomy of the Millennium Falcon.

    Returns:
        - length_without_refuel (int): the length of the path according to the distance in the universe_graph INCLUDING refuel steps.
        - length_without_refuel (int): the length of the path according to the distance in the universe_graph WITHOUT refuel steps.
        - n_refuel (int): the number of refuel steps.

    """

    path_edge_weights = [
        universe_graph[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1)
    ]
    length_without_refuel = sum(path_edge_weights)
    n_refuel = 0
    for i in range(1, len(path) - 1):
        incoming_w = universe_graph[path[i - 1]][path[i]]["weight"]
        outgoing_w = universe_graph[path[i]][path[i + 1]]["weight"]
        if (incoming_w + outgoing_w) >= autonomy:
            n_refuel += 1
    total_length = n_refuel + length_without_refuel

    return total_length, length_without_refuel, n_refuel


def compute_path_odds(
    path: list, universe_graph: nx.Graph, empire_dict: dict, millenium_dict: dict
) -> (float, list):
    """
    Compute the optimal odds possible given a path

    Parameters:
        - path (list): a list of the names of the nodes constituting the path from departure to arrival.
        - universe_graph (nx.Graph): NetworkX graph representing the possible routes in the universe.
        - empire_dict (dict): dict object containing information about the Empire Communications.
        - millenium_dict (dict): dict object containing information about the Millennium Falcon.

    Returns:
        - odds (float): the odds of success of the path.
        - itinerary (list[tuple] | None): the associated strategy to achieve the odds contains the arrival
                                          and departure days for each planet in the path. None if the odds are 0.
    """
    autonomy = millenium_dict["autonomy"]

    bounty_dict = defaultdict(set)
    for bounty in empire_dict["bounty_hunters"]:
        bounty_dict[bounty["planet"]].add(bounty["day"])

    path_edge_weights = [
        universe_graph[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1)
    ]
    total_length, length_without_refuel, n_refuel = compute_path_length(
        path, universe_graph, autonomy
    )

    if total_length > int(empire_dict["countdown"]):
        return 0, None

    # split planets into two groups:
    # 1 - where the falcon must refuel, i.e. planets where incoming and outgoing travels are above the falcon autonomy
    # 2 - the others planets

    forced_refuel = []
    may_stop_or_refuel = [path[0]]
    for i in range(1, len(path) - 1):
        incoming_w = universe_graph[path[i - 1]][path[i]]["weight"]
        outgoing_w = universe_graph[path[i]][path[i + 1]]["weight"]
        if (incoming_w + outgoing_w) >= autonomy:
            forced_refuel.append(path[i])

        may_stop_or_refuel.append(path[i])

    # compute the number of possible stops and refuels among the path
    allowed_stop_or_refuel = (
        empire_dict["countdown"] - length_without_refuel - len(forced_refuel)
    )

    itinerary_dates = []
    best_stops = None

    if allowed_stop_or_refuel > 0:
        lowest_encounter = empire_dict["countdown"]

        # enumerate all possibilities to stops among the path (taking forced stop into account)
        for stops in itertools.combinations_with_replacement(
            may_stop_or_refuel, allowed_stop_or_refuel
        ):
            stops = list(stops) + forced_refuel
            itinerary_dates = []
            stops_per_planet = {planet: stops.count(planet) for planet in path}

            fuel = autonomy
            for idx_planet, planet in enumerate(path):
                if idx_planet == 0:
                    itinerary_dates.append((0, stops_per_planet[planet]))
                else:
                    arrival_day = (
                        itinerary_dates[-1][-1] + path_edge_weights[idx_planet - 1]
                    )

                    # while following the path check if fuel is never empty
                    # (i.e. stop arrangement would make the path infeasible)
                    fuel -= path_edge_weights[idx_planet - 1]
                    if fuel < 0:
                        break
                    leaving_day = arrival_day + stops_per_planet[planet]

                    # if the falcon stop one day ore more, it always refuels
                    if leaving_day - arrival_day > 0:
                        fuel = autonomy
                    itinerary_dates.append((arrival_day, leaving_day))

            nb_encounters = compute_encounters(path, itinerary_dates, bounty_dict)

            if nb_encounters < lowest_encounter:
                lowest_encounter = nb_encounters
                best_stops = itinerary_dates.copy()
    else:
        # if all stops are forced, only one arrangement need to be checked
        for idx_planet, planet in enumerate(path):
            if idx_planet == 0:
                itinerary_dates.append((0, 0))
            else:
                arrival_day = (
                    itinerary_dates[-1][-1] + path_edge_weights[idx_planet - 1]
                )
                leaving_day = arrival_day
                if planet in forced_refuel:
                    leaving_day += 1

                itinerary_dates.append((arrival_day, leaving_day))
        lowest_encounter = compute_encounters(path, itinerary_dates, bounty_dict)
        best_stops = itinerary_dates.copy()

    # odds computation based on the number of encounters with bounty hunters
    odds = (1 - sum(9**i / (10 ** (i + 1)) for i in range(lowest_encounter))) * 100
    return odds, best_stops


def compute_encounters(path: list, itinerary_dates: list, bounty_presence: dict) -> int:
    """
    Compute the number of encounters with bounty hunters following a path and an itinerary

    Parameters:
        - path (list): a list of the names of the nodes constituting the path from departure to arrival.
        - itinerary (list[tuple]): the associated strategy to achieve the odds contains the arrival
                                   and departure days for each planet in the path.
        - bounty_presence (dict[set]): dict object containing the set of day when bounty hunters are present on each planet.

    Returns:
        - encounters (int): the number of encounters with bounty hunters.
    """
    itinerary_dates
    falcon_presence = {}
    day = 0

    # convert the itinerary and path in a presence dict just as bounty_presence format.
    for planet, (arrival, departure) in zip(path, itinerary_dates):
        falcon_presence[planet] = set(i for i in range(arrival, departure + 1))
        day = departure + 1

    bounty_planets = set(bounty_presence)
    falcon_planets = set(falcon_presence)

    # the number of encounter is the size of the intersecting sets summed over the planets.
    encounters = 0
    for planet in bounty_planets.intersection(falcon_planets):
        encounters += len(bounty_presence[planet].intersection(falcon_presence[planet]))

    return encounters


def compute_odds(
    millenium_path: str, empire_path: str, verbose: bool = False
) -> (float, list):
    """
    Computes the odds of success given paths to the Millennium Falcon and Empire Com files.

    Parameters:
        - millenium_path (str): path to the Millennium Falcon .json file
        - empire_path (str): path to the Empire Communication .json file
        - verbose (bool): switch for verbosity

    Returns:
        - odds (float | None): the odds of success, None if input paths or files are wrong.
        - itinerary (list[str] | None): The prettified strings for each step in the itinerary,
                                      if an itinerary is possible, None otherwise.

    """
    # print(logger.level)
    logger = logging.getLogger('R2D2')
    logger.setLevel(logging.INFO if verbose else logging.CRITICAL)

    millenium_dict, empire_dict = get_json_contents(millenium_path, empire_path)
    if millenium_dict is None or empire_dict is None:
        logger.warning(" Abort Mission !")
        return None, None

    # check weither route_db is absolute or relative path
    if os.path.isfile(millenium_dict["routes_db"]):
        db_path = millenium_dict["routes_db"]
    else:
        db_directory = os.path.dirname(millenium_path)
        db_path = os.path.join(db_directory, millenium_dict["routes_db"])
    universe_graph = build_unvierse_graph(db_path, millenium_dict)

    if universe_graph is None:
        return None, None

    # check if there is a shortest path in the graph between departure and arrival
    try:
        shortest_path = nx.algorithms.shortest_path(
            universe_graph,
            source=millenium_dict["departure"],
            target=millenium_dict["arrival"],
            weight="weight",
        )

    except nx.NetworkXNoPath:
        logger.info(
            " No path found between {} and {}. Its odds of success are 0%.".format(
                millenium_dict["departure"], millenium_dict["arrival"]
            )
        )
        return 0, None

    # check if the shortest path is too long
    path_length, path_length_without_refuel, n_refuel = compute_path_length(
        shortest_path, universe_graph, millenium_dict["autonomy"]
    )

    if path_length > int(empire_dict["countdown"]):
        logger.info(
            " Shortest path is too slow for the Falcon to reach {} before the Death Star annihilates the planet... Its odds of success are 0%.".format(
                millenium_dict["arrival"]
            )
        )
        return 0, None

    # The mission is possible now we must look at all possible path from departure to arrival
    # and compute their odds.
    max_odds = 0
    best_itinerary = None
    best_path = None
    for path in nx.shortest_simple_paths(
        universe_graph,
        millenium_dict["departure"],
        millenium_dict["arrival"],
        weight="weight",
    ):
        odds, itinerary = compute_path_odds(
            path, universe_graph, empire_dict, millenium_dict
        )
        if odds > max_odds:
            max_odds = odds
            best_itinerary = itinerary
            best_path = path
        max_odds = max(odds, max_odds)

    logger.info(
        " The Falcon can reach {} before the Death Star annihilates the planet! Its odds of success are {}%.".format(
            millenium_dict["arrival"], max_odds
        )
    )
    return max_odds, prettify_path(best_path, best_itinerary)


def parse_command_line():
    """
    Handle the argument parsing for the CLI.
    """
    parser = argparse.ArgumentParser("parser", add_help=True)

    parser.add_argument(
        "millenium_path",
        default="",
        type=str,
        help="Path to the Millenium Falcon config file",
    )
    parser.add_argument(
        "empire_path", default="", type=str, help="Path to the Empire config file"
    )
    parser.add_argument(
        "--verbose", help="Display logs", action=argparse.BooleanOptionalAction
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_command_line()
    odds, itinerary = compute_odds(
        args.millenium_path, args.empire_path, verbose=args.verbose
    )
    if odds is not None:
        print("The odds of success are {:.1f}%.".format(odds))
